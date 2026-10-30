"""Adapter for any OpenAI-compatible chat API: Groq, Google Gemini, OpenRouter, a local Ollama, and more.

It converts the assistant's internal "content blocks" messages (Anthropic style) to the OpenAI chat format and
back, so the agents and tools do not change at all. Uses `httpx`, which is already installed with the project.
"""
from __future__ import annotations

import json
import logging
import time

import httpx

from .base import LLMError, LLMResponse, LLMUnavailable, ToolCall

log = logging.getLogger("assistant.llm")

# provider name -> (base_url, default_model, needs_api_key)
PROVIDERS: dict[str, tuple[str, str, bool]] = {
    "groq": ("https://api.groq.com/openai/v1", "openai/gpt-oss-120b", True),
    "gemini": ("https://generativelanguage.googleapis.com/v1beta/openai", "gemini-2.5-flash", True),
    "openrouter": ("https://openrouter.ai/api/v1", "google/gemma-4-31b-it:free", True),
    "ollama": ("http://localhost:11434/v1", "llama3.1", False),
}


def _to_openai_messages(system: str, messages: list[dict]) -> list[dict]:
    out: list[dict] = [{"role": "system", "content": system}]
    for m in messages:
        role, content = m["role"], m["content"]
        if isinstance(content, str):
            out.append({"role": role, "content": content})
            continue
        if role == "assistant":
            text = "".join(b.get("text", "") for b in content if b.get("type") == "text")
            calls = [
                {"id": b["id"], "type": "function",
                 "function": {"name": b["name"], "arguments": json.dumps(b.get("input") or {})}}
                for b in content if b.get("type") == "tool_use"
            ]
            msg: dict = {"role": "assistant", "content": text or None}
            if calls:
                msg["tool_calls"] = calls
            out.append(msg)
        else:  # user turn that may carry tool results
            texts = []
            for b in content:
                if b.get("type") == "tool_result":
                    body = b.get("content", "")
                    if not isinstance(body, str):
                        body = json.dumps(body, default=str)
                    if b.get("is_error"):
                        body = f"ERROR: {body}"
                    out.append({"role": "tool", "tool_call_id": b["tool_use_id"], "content": body})
                elif b.get("type") == "text":
                    texts.append(b.get("text", ""))
            if texts:
                out.append({"role": "user", "content": "\n".join(texts)})
    return out


class OpenAICompatLLM:
    def __init__(self, base_url: str, api_key: str, model: str, timeout: float = 30.0, max_retries: int = 2,
                 client: httpx.Client | None = None):
        self.model = model
        self.max_retries = max_retries
        self.url = base_url.rstrip("/") + "/chat/completions"
        headers = {"Content-Type": "application/json"}
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"
        self.client = client or httpx.Client(timeout=timeout, headers=headers)

    def _post(self, payload: dict) -> httpx.Response:
        last: Exception | None = None
        for attempt in range(self.max_retries + 1):
            try:
                resp = self.client.post(self.url, json=payload)
            except (httpx.TimeoutException, httpx.TransportError) as e:
                last = LLMUnavailable(f"model unreachable: {type(e).__name__}")
            else:
                if resp.status_code == 429 or resp.status_code >= 500:
                    last = LLMUnavailable(f"model busy or rate limited ({resp.status_code})")
                else:
                    return resp
            if attempt < self.max_retries:
                time.sleep(1.5 * (attempt + 1))
        raise last  # type: ignore[misc]

    def complete(self, *, system: str, messages: list[dict], tools: list[dict],
                 max_tokens: int = 1024, force_tool: str | None = None) -> LLMResponse:
        payload: dict = {"model": self.model, "max_tokens": max_tokens,
                         "messages": _to_openai_messages(system, messages)}
        if tools:
            payload["tools"] = [
                {"type": "function",
                 "function": {"name": t["name"], "description": t["description"], "parameters": t["input_schema"]}}
                for t in tools
            ]
            if force_tool:
                payload["tool_choice"] = {"type": "function", "function": {"name": force_tool}}

        resp = self._post(payload)
        if resp.status_code == 400 and force_tool:
            # Some free models reject a *named* tool choice; "required" still forces a tool call.
            payload["tool_choice"] = "required"
            resp = self._post(payload)
        if resp.status_code != 200:
            detail = ""
            try:
                detail = str(resp.json().get("error", {}).get("message", ""))[:200]
            except Exception:
                pass
            log.warning("LLM request rejected: %s %s", resp.status_code, detail)
            raise LLMError(f"model request rejected ({resp.status_code})")

        try:
            msg = resp.json()["choices"][0]["message"]
        except (KeyError, IndexError, ValueError) as e:
            raise LLMUnavailable("model returned an unreadable response") from e

        calls: list[ToolCall] = []
        for tc in msg.get("tool_calls") or []:
            fn = tc.get("function", {})
            try:
                args = json.loads(fn.get("arguments") or "{}")
            except ValueError:
                args = {}
            calls.append(ToolCall(id=tc.get("id") or f"call_{len(calls)}", name=fn.get("name", ""),
                                  input=args if isinstance(args, dict) else {}))
        return LLMResponse(text=(msg.get("content") or "").strip(), tool_calls=calls)
