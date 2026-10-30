"""Tool framework. The LLM never touches the database: it can only ask for one of the registered tools,
with arguments that are validated here, under an authorization check made in code."""
from __future__ import annotations

import datetime as dt
import logging
import time
from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any, Callable

from pydantic import BaseModel, ConfigDict, ValidationError
from sqlalchemy.orm import Session

from ..auth import Principal
from ..config import Settings

log = logging.getLogger("assistant.tools")


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class ToolError(Exception):
    """A problem the model/user may be told about (message must be safe to show)."""


@dataclass
class ToolRecord:
    agent: str
    tool: str
    status: str  # ok | error | denied
    error: str = ""
    duration_ms: int = 0


@dataclass
class ToolContext:
    principal: Principal
    store: Session          # READ-ONLY shop database
    agent: Session          # assistant's own database
    settings: Settings
    task_id: str
    now: dt.datetime        # timezone-aware UTC "current time" (injectable for tests)
    records: list[ToolRecord] = field(default_factory=list)

    @property
    def business_id(self) -> str:
        return self.settings.business_id


@dataclass(frozen=True)
class ToolSpec:
    name: str
    description: str
    input_model: type[StrictModel]
    handler: Callable[[ToolContext, Any], dict]
    agents: frozenset[str]   # which specialist agents may be offered this tool
    roles: frozenset[str]    # which user roles may run it


_REGISTRY: dict[str, ToolSpec] = {}
ALL_ROLES = frozenset({"anonymous", "customer", "staff", "admin"})
STAFF = frozenset({"staff", "admin"})
ADMIN_ONLY = frozenset({"admin"})


def tool(name: str, description: str, input_model: type[StrictModel], agents: set[str], roles: frozenset[str]):
    def deco(fn):
        _REGISTRY[name] = ToolSpec(name, description, input_model, fn, frozenset(agents), roles)
        return fn
    return deco


def get_tool(name: str) -> ToolSpec | None:
    return _REGISTRY.get(name)


def schemas_for(agent: str, role: str) -> list[dict]:
    """Only advertise tools this agent AND this role may use (defence in depth; execute() re-checks)."""
    out = []
    for t in _REGISTRY.values():
        if agent in t.agents and role in t.roles:
            schema = t.input_model.model_json_schema()
            schema.pop("title", None)
            out.append({"name": t.name, "description": t.description, "input_schema": schema})
    return out


def execute(ctx: ToolContext, agent: str, name: str, raw_input: Any) -> dict:
    """Run one tool call. ALWAYS returns a dict: {"ok": True, "data": ...} or {"ok": False, "error": ...}."""
    t0 = time.perf_counter()

    def finish(status: str, payload: dict, error: str = "") -> dict:
        ctx.records.append(ToolRecord(agent, name, status, error, int((time.perf_counter() - t0) * 1000)))
        return payload

    spec = _REGISTRY.get(name)
    if spec is None:
        return finish("error", {"ok": False, "error": f"Unknown tool '{name}'."}, "unknown tool")
    if agent not in spec.agents or ctx.principal.role not in spec.roles:
        log.warning("DENIED tool=%s agent=%s role=%s", name, agent, ctx.principal.role)
        return finish("denied", {"ok": False, "error": "You are not authorized to use this tool."}, "not authorized")
    if not isinstance(raw_input, dict):
        return finish("error", {"ok": False, "error": "Tool input must be a JSON object."}, "bad input")
    try:
        args = spec.input_model.model_validate(raw_input)
    except ValidationError as e:
        msg = "; ".join(f"{'.'.join(str(p) for p in err['loc'])}: {err['msg']}" for err in e.errors()[:4])
        return finish("error", {"ok": False, "error": f"Invalid input - {msg}"}, "invalid input")
    try:
        data = spec.handler(ctx, args)
        return finish("ok", {"ok": True, "data": data})
    except ToolError as e:
        return finish("error", {"ok": False, "error": str(e)}, str(e))
    except Exception:  # never leak internals to the model or the user
        log.exception("tool %s crashed", name)
        return finish("error", {"ok": False, "error": "Internal error while running this tool."}, "internal error")


def money(x: Decimal | float | int | None) -> int | float | None:
    """JSON-friendly money: whole rupees stay ints."""
    if x is None:
        return None
    d = Decimal(str(x)).quantize(Decimal("0.01"))
    return int(d) if d == d.to_integral_value() else float(d)
