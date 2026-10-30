"""FastAPI application. Run with:  uvicorn app.main:create_app --factory --port 8001 --reload"""
from __future__ import annotations

import logging
import re

from fastapi import Depends, FastAPI, Header, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import select, text

from .agents.manager import Manager, new_task_id
from .auth import AuthError, Principal, resolve_principal
from .config import Settings, get_settings
from .db import Database
from .drafts import draft_view
from .guardrails import check_claims, collect_facts
from .llm.anthropic_client import UnconfiguredLLM, build_llm
from .models_agent import AgentTask, Draft, ToolLog
from .ratelimit import RateLimiter
from .schemas import ApproveRequest, ChatRequest, ChatResponse, DraftUpdate, RejectRequest
from .timeutil import utcnow
from .tools import ToolContext

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")


def create_app(settings: Settings | None = None, llm=None, db: Database | None = None, clock=utcnow) -> FastAPI:
    settings = settings or get_settings()
    db = db or Database.from_settings(settings)
    db.init_agent_schema()                       # idempotent: creates the assistant's own tables if missing
    llm = llm or build_llm(settings)
    manager = Manager(llm, settings)
    limiter = RateLimiter(settings.rate_limit_per_minute)

    app = FastAPI(title=f"{settings.store_name} Business Assistant", version="1.0.0")
    app.add_middleware(CORSMiddleware, allow_origins=settings.origins, allow_methods=["GET", "POST", "PATCH"],
                       allow_headers=["Authorization", "Content-Type"])

    # ----- dependencies -------------------------------------------------------------------------------------
    def principal_dep(authorization: str | None = Header(None)) -> Principal:
        try:
            with db.store_session() as s:
                return resolve_principal(s, authorization)
        except AuthError as e:
            raise HTTPException(401, str(e))

    def staff_dep(p: Principal = Depends(principal_dep)) -> Principal:
        if not p.is_staff:
            raise HTTPException(403, "Staff access required")
        return p

    # ----- routes -------------------------------------------------------------------------------------------
    @app.get("/health")
    def health():
        try:
            with db.store_session() as s:
                s.execute(text("SELECT 1"))
            store_ok = True
        except Exception:
            store_ok = False
        return {"status": "ok" if store_ok else "degraded", "store_db": store_ok,
                "llm_configured": not isinstance(llm, UnconfiguredLLM)}

    @app.get("/me")
    def me(p: Principal = Depends(principal_dep)):
        return {"role": p.role, "email": p.email, "allowed_agents": sorted(p.allowed_agents)}

    @app.post("/chat", response_model=ChatResponse, response_model_exclude_none=True)
    def chat(body: ChatRequest, request: Request, p: Principal = Depends(principal_dep)):
        key = p.user_id or (request.client.host if request.client else "unknown")
        if not limiter.allow(key):
            raise HTTPException(429, "Too many requests - please wait a moment.")
        conversation = "\n".join(f"{t.role.capitalize()}: {t.content[:500]}" for t in body.history[-6:])
        with db.store_session() as store, db.agent_session() as agent:
            ctx = ToolContext(principal=p, store=store, agent=agent, settings=settings,
                              task_id=new_task_id(), now=clock())
            r = manager.handle(ctx, body.message, conversation)
        resp = ChatResponse(task_id=r.task_id, status=r.status, answer=r.answer, escalated=r.escalated)
        if p.is_staff:   # internals (tool outputs, trace) are for staff only
            resp.agents_used, resp.plan_source, resp.duration_ms = r.agents_used, r.plan_source, r.duration_ms
            resp.steps = [vars(s) for s in r.steps]
            resp.structured = r.structured
        return resp

    @app.get("/history")
    def history(limit: int = Query(30, ge=1, le=100), p: Principal = Depends(staff_dep)):
        with db.agent_session() as s:
            tasks = s.scalars(select(AgentTask).where(AgentTask.business_id == settings.business_id)
                              .order_by(AgentTask.created_at.desc()).limit(limit)).all()
            logs = s.scalars(select(ToolLog).where(ToolLog.task_id.in_([t.id for t in tasks]),
                                                   ToolLog.business_id == settings.business_id)).all() if tasks else []
            by_task: dict[str, list] = {}
            for lg in logs:
                by_task.setdefault(lg.task_id, []).append(
                    {"agent": lg.agent, "tool": lg.tool, "status": lg.status, "duration_ms": lg.duration_ms})
            return {"items": [{
                "task_id": t.id, "created_at": t.created_at.isoformat() + "Z", "role": t.role,
                "request": t.request_text, "status": t.status, "agents": t.agents_used, "error": t.error,
                "duration_ms": t.duration_ms, "answer_preview": t.answer_preview, "tools": by_task.get(t.id, []),
            } for t in tasks]}

    def _get_draft(s, draft_id: str) -> Draft:
        d = s.scalars(select(Draft).where(Draft.id == draft_id, Draft.business_id == settings.business_id)).first()
        if d is None:
            raise HTTPException(404, "Draft not found")
        return d

    @app.get("/drafts")
    def list_drafts(status: str | None = Query(None, max_length=16), kind: str | None = Query(None, max_length=30),
                    limit: int = Query(50, ge=1, le=100), p: Principal = Depends(staff_dep)):
        with db.agent_session() as s:
            q = select(Draft).where(Draft.business_id == settings.business_id)
            if status:
                q = q.where(Draft.status == status)
            if kind:
                q = q.where(Draft.kind == kind)
            return {"items": [draft_view(d) for d in s.scalars(q.order_by(Draft.created_at.desc()).limit(limit))]}

    @app.patch("/drafts/{draft_id}")
    def edit_draft(draft_id: str, body: DraftUpdate, p: Principal = Depends(staff_dep)):
        with db.agent_session() as s, db.store_session() as store:
            d = _get_draft(s, draft_id)
            if d.status not in ("draft", "pending_review"):
                raise HTTPException(409, f"A {d.status} draft can no longer be edited")
            if body.title is not None:
                d.title = body.title
            if body.body is not None:
                d.body = body.body
            if d.kind != "support_escalation":   # a human edit can introduce new claims -> re-check
                d.warnings = check_claims(f"{d.title}\n{d.body}", collect_facts(store, d.product_skus or [], clock()))
            s.commit()
            return draft_view(d)

    @app.post("/drafts/{draft_id}/approve")
    def approve_draft(draft_id: str, body: ApproveRequest, p: Principal = Depends(staff_dep)):
        with db.agent_session() as s:
            d = _get_draft(s, draft_id)
            if d.status not in ("draft", "pending_review"):
                raise HTTPException(409, f"Draft is already {d.status}")
            if d.warnings and not body.acknowledge_warnings:
                raise HTTPException(409, "This draft has unverified claims. Fix them, or approve with acknowledge_warnings=true.")
            d.status = "resolved" if d.kind == "support_escalation" else "approved"
            d.reviewed_by = p.user_id
            s.commit()
            return draft_view(d)     # NOTE: approving never publishes or sends anything in this version

    @app.post("/drafts/{draft_id}/reject")
    def reject_draft(draft_id: str, body: RejectRequest, p: Principal = Depends(staff_dep)):
        with db.agent_session() as s:
            d = _get_draft(s, draft_id)
            if d.status not in ("draft", "pending_review"):
                raise HTTPException(409, f"Draft is already {d.status}")
            d.status, d.reviewed_by, d.review_note = "rejected", p.user_id, body.note
            s.commit()
            return draft_view(d)

    app.state.db, app.state.manager, app.state.limiter = db, manager, limiter
    return app
