"""A tiny, provider-neutral interface so the agents never depend on one vendor's SDK.

Messages use the common "content blocks" shape:
    {"role": "user",      "content": "text"}
    {"role": "assistant", "content": [{"type":"text",...}, {"type":"tool_use", "id", "name", "input"}]}
    {"role": "user",      "content": [{"type":"tool_result", "tool_use_id", "content", "is_error"}]}
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol


class LLMError(Exception):
    """The model call failed in a way retrying will not fix (bad request, auth error, ...)."""


class LLMUnavailable(LLMError):
    """The model could not be reached: timeout, network error, rate limit, or not configured."""


@dataclass
class ToolCall:
    id: str
    name: str
    input: dict


@dataclass
class LLMResponse:
    text: str = ""
    tool_calls: list[ToolCall] = field(default_factory=list)

    def assistant_blocks(self) -> list[dict]:
        blocks: list[dict] = []
        if self.text:
            blocks.append({"type": "text", "text": self.text})
        for c in self.tool_calls:
            blocks.append({"type": "tool_use", "id": c.id, "name": c.name, "input": c.input})
        return blocks


class LLMClient(Protocol):
    def complete(self, *, system: str, messages: list[dict], tools: list[dict],
                 max_tokens: int = 1024, force_tool: str | None = None) -> LLMResponse: ...
