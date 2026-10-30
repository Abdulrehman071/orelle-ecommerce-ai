"""The assistant's OWN tables (separate from the shop database)."""
from __future__ import annotations

import datetime as dt
import uuid

from sqlalchemy import JSON, DateTime, Integer, String, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


def _now() -> dt.datetime:
    return dt.datetime.now(dt.timezone.utc).replace(tzinfo=None)


def _uuid() -> str:
    return uuid.uuid4().hex


class AgentBase(DeclarativeBase):
    pass


class AgentTask(AgentBase):
    """One row per user request: who asked, which agents ran, did it work, how long it took."""
    __tablename__ = "assistant_task"
    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_uuid)
    business_id: Mapped[str] = mapped_column(String(50), index=True)
    user_id: Mapped[str | None] = mapped_column(String(32), nullable=True)
    role: Mapped[str] = mapped_column(String(12))
    request_text: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(12))  # completed | partial | failed | refused
    agents_used: Mapped[list] = mapped_column(JSON, default=list)
    answer_preview: Mapped[str] = mapped_column(Text, default="")
    error: Mapped[str] = mapped_column(Text, default="")
    duration_ms: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[dt.datetime] = mapped_column(DateTime, default=_now, index=True)


class ToolLog(AgentBase):
    """One row per tool call (including denied and failed calls)."""
    __tablename__ = "assistant_tool_log"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    task_id: Mapped[str] = mapped_column(String(32), index=True)
    business_id: Mapped[str] = mapped_column(String(50), index=True)
    agent: Mapped[str] = mapped_column(String(20))
    tool: Mapped[str] = mapped_column(String(50))
    status: Mapped[str] = mapped_column(String(10))  # ok | error | denied
    error: Mapped[str] = mapped_column(Text, default="")
    duration_ms: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[dt.datetime] = mapped_column(DateTime, default=_now)


class Draft(AgentBase):
    """Anything the assistant writes for a human to review: marketing copy or a support escalation."""
    __tablename__ = "assistant_draft"
    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_uuid)
    business_id: Mapped[str] = mapped_column(String(50), index=True)
    task_id: Mapped[str] = mapped_column(String(32), index=True)
    kind: Mapped[str] = mapped_column(String(30))     # product_description | facebook_post | ... | support_escalation
    title: Mapped[str] = mapped_column(String(200))
    body: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(16))   # draft | approved | rejected | pending_review | resolved
    warnings: Mapped[list] = mapped_column(JSON, default=list)
    product_skus: Mapped[list] = mapped_column(JSON, default=list)
    meta: Mapped[dict] = mapped_column(JSON, default=dict)  # e.g. escalation reason / customer contact
    created_by: Mapped[str | None] = mapped_column(String(32), nullable=True)
    reviewed_by: Mapped[str | None] = mapped_column(String(32), nullable=True)
    review_note: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[dt.datetime] = mapped_column(DateTime, default=_now, index=True)
    updated_at: Mapped[dt.datetime] = mapped_column(DateTime, default=_now, onupdate=_now)
