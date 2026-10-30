"""Tests OUR conversion/error-mapping code with a stubbed SDK client. This is NOT a live API test."""
from types import SimpleNamespace as NS

import anthropic
import httpx
import pytest

from app.llm.anthropic_client import AnthropicLLM, UnconfiguredLLM, build_llm
from app.llm.base import LLMError, LLMUnavailable
from conftest import make_settings

REQ = httpx.Request("POST", "https://api.anthropic.com/v1/messages")


class Stub:
    def __init__(self, result=None, exc=None):
        self.result, self.exc, self.kwargs = result, exc, None
        self.messages = NS(create=self._create)

    def _create(self, **kw):
        self.kwargs = kw
        if self.exc:
            raise self.exc
        return self.result


def test_request_and_response_conversion():
    stub = Stub(NS(content=[NS(type="text", text=" Hello "), NS(type="tool_use", id="t1", name="search_products", input={"query": "tee"})]))
    llm = AnthropicLLM("k", "claude-test", client=stub)
    tools = [{"name": "search_products", "description": "d", "input_schema": {"type": "object"}, "extra": "dropped"}]
    r = llm.complete(system="SYS", messages=[{"role": "user", "content": "hi"}], tools=tools, max_tokens=123, force_tool="search_products")
    assert stub.kwargs == {"model": "claude-test", "max_tokens": 123, "system": "SYS", "messages": [{"role": "user", "content": "hi"}],
                           "tools": [{"name": "search_products", "description": "d", "input_schema": {"type": "object"}}],
                           "tool_choice": {"type": "tool", "name": "search_products"}}
    assert r.text == "Hello" and r.tool_calls[0].name == "search_products" and r.tool_calls[0].input == {"query": "tee"}
    assert r.assistant_blocks() == [{"type": "text", "text": "Hello"},
                                    {"type": "tool_use", "id": "t1", "name": "search_products", "input": {"query": "tee"}}]


def test_no_tools_means_no_tool_params():
    stub = Stub(NS(content=[NS(type="text", text="x")]))
    AnthropicLLM("k", "m", client=stub).complete(system="s", messages=[], tools=[])
    assert "tools" not in stub.kwargs and "tool_choice" not in stub.kwargs


@pytest.mark.parametrize("exc,expected", [
    (anthropic.APITimeoutError(request=REQ), LLMUnavailable),
    (anthropic.APIConnectionError(request=REQ), LLMUnavailable),
    (anthropic.RateLimitError("slow down", response=httpx.Response(429, request=REQ), body=None), LLMUnavailable),
    (anthropic.InternalServerError("oops", response=httpx.Response(500, request=REQ), body=None), LLMUnavailable),
    (anthropic.BadRequestError("bad", response=httpx.Response(400, request=REQ), body=None), LLMError),
    (anthropic.AuthenticationError("no", response=httpx.Response(401, request=REQ), body=None), LLMError),
])
def test_sdk_errors_are_mapped(exc, expected):
    with pytest.raises(expected) as e:
        AnthropicLLM("k", "m", client=Stub(exc=exc)).complete(system="s", messages=[], tools=[])
    assert type(e.value) is expected                     # LLMError must NOT be the 'retryable' subclass


def test_build_llm_without_key_is_unconfigured_and_with_key_builds_client(store_path):
    assert isinstance(build_llm(make_settings(store_path)), UnconfiguredLLM)
    assert isinstance(build_llm(make_settings(store_path, anthropic_api_key="sk-test")), AnthropicLLM)   # no network call made
    with pytest.raises(LLMUnavailable):
        UnconfiguredLLM().complete(system="s", messages=[], tools=[])
