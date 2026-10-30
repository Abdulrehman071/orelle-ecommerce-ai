"""Adapter for the Anthropic Messages API (tool use).

NOTE: this adapter's request/response conversion is unit-tested with a stubbed SDK client, but it has
NOT been exercised against the live API in development because no API key was available. See README.
"""
from __future__ import annotations

import logging

from .base import LLMError, LLMResponse, LLMUnavailable, ToolCall

log = logging.getLogger("assistant.llm")


class UnconfiguredLLM:
    """Used when ANTHROPIC_API_KEY is missing: the service still starts, but chat answers 'not configured'."""

    def complete(self, **_kwargs) -> LLMResponse:
        raise LLMUnavailable("ANTHROPIC_API_KEY is not set")


class AnthropicLLM:
    def __init__(self, api_key: str, model: str, timeout: float = 30.0, max_retries: int = 2, client=None):
        import anthropic

        self._sdk = anthropic
        self.model = model
        self.client = client or anthropic.Anthropic(api_key=api_key, timeout=timeout, max_retries=max_retries)

    def complete(self, *, system: str, messages: list[dict], tools: list[dict],
                 max_tokens: int = 1024, force_tool: str | None = None) -> LLMResponse:
        kwargs: dict = {"model": self.model, "max_tokens": max_tokens, "system": system, "messages": messages}
        if tools:
            kwargs["tools"] = [
                {"name": t["name"], "description": t["description"], "input_schema": t["input_schema"]} for t in tools
            ]
            if force_tool:
                kwargs["tool_choice"] = {"type": "tool", "name": force_tool}
        sdk = self._sdk
        try:
            resp = self.client.messages.create(**kwargs)
        except (sdk.APITimeoutError, sdk.APIConnectionError) as e:
            raise LLMUnavailable(f"model unreachable: {type(e).__name__}") from e
        except sdk.RateLimitError as e:
            raise LLMUnavailable("model rate limit reached") from e
        except sdk.APIStatusError as e:
            if e.status_code >= 500:
                raise LLMUnavailable(f"model service error {e.status_code}") from e
            raise LLMError(f"model request rejected ({e.status_code})") from e

        text = "".join(b.text for b in resp.content if getattr(b, "type", "") == "text")
        calls = [ToolCall(id=b.id, name=b.name, input=dict(b.input or {}))
                 for b in resp.content if getattr(b, "type", "") == "tool_use"]
        return LLMResponse(text=text.strip(), tool_calls=calls)


def build_llm(settings):
    provider = (settings.llm_provider or ("anthropic" if settings.anthropic_api_key else "")).strip().lower()

    if provider in ("", "anthropic"):
        if not settings.anthropic_api_key:
            log.warning("No LLM configured - the assistant will answer 'not configured'.")
            return UnconfiguredLLM()
        return AnthropicLLM(settings.anthropic_api_key, settings.anthropic_model,
                            settings.llm_timeout_seconds, settings.llm_max_retries)

    from .openai_compat_client import PROVIDERS, OpenAICompatLLM

    if provider not in PROVIDERS:
        log.warning("Unknown LLM_PROVIDER %r (use one of: anthropic, %s)", provider, ", ".join(PROVIDERS))
        return UnconfiguredLLM()
    base_url, default_model, needs_key = PROVIDERS[provider]
    if needs_key and not settings.llm_api_key:
        log.warning("LLM_PROVIDER=%s but LLM_API_KEY is empty - the assistant will answer 'not configured'.", provider)
        return UnconfiguredLLM()
    return OpenAICompatLLM(settings.llm_base_url or base_url, settings.llm_api_key,
                           settings.llm_model or default_model,
                           settings.llm_timeout_seconds, settings.llm_max_retries)
