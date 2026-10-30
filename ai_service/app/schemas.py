from __future__ import annotations

import re
from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator

_CTRL = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f]")


class HistoryTurn(BaseModel):
    role: Literal["user", "assistant"]
    content: str = Field(..., max_length=2000)


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=2000)
    history: list[HistoryTurn] = Field(default_factory=list, max_length=12)

    @field_validator("message")
    @classmethod
    def _clean(cls, v: str) -> str:
        v = _CTRL.sub("", v).strip()
        if not v:
            raise ValueError("message must not be empty")
        return v


class ChatResponse(BaseModel):
    task_id: str
    status: Literal["completed", "partial", "failed", "refused"]
    answer: str
    escalated: bool = False
    # Internal details are only returned to staff/admin
    agents_used: list[str] | None = None
    plan_source: str | None = None
    duration_ms: int | None = None
    steps: list[dict[str, Any]] | None = None
    structured: dict[str, Any] | None = None


class DraftUpdate(BaseModel):
    title: str | None = Field(None, min_length=2, max_length=200)
    body: str | None = Field(None, min_length=1, max_length=4000)


class ApproveRequest(BaseModel):
    acknowledge_warnings: bool = False


class RejectRequest(BaseModel):
    note: str = Field("", max_length=500)
