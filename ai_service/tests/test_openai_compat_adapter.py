import json

import httpx
import pytest

from app.config import Settings
from app.llm.anthropic_client import UnconfiguredLLM, build_llm
from app.llm.base import LLMError, LLMUnavailable
from app.llm.openai_compat_client import OpenAICompatLLM

TOOL = {"name": "search_products", "description": "d",
        "input_schema": {"type": "object", "properties": {"q": {"type": "string"}}}}


def make(handler, retries=0):
    client = httpx.Client(transport=httpx.MockTransport(handler))
    return OpenAICompatLLM("http://x/v1", "k", "m", max_retries=retries, client=client)


def test_text_answer_and_message_conversion():
    seen = {}

    def handler(req):
        seen.update(json.loads(req.content))
        return httpx.Response(200, json={"choices": [{"message": {"content": " hello "}}]})

    msgs = [
        {"role": "user", "content": "hi"},
        {"role": "assistant", "content": [{"type": "text", "text": "ok"},
                                          {"type": "tool_use", "id": "t1", "name": "search_products", "input": {"q": "x"}}]},
        {"role": "user", "content": [{"type": "tool_result", "tool_use_id": "t1", "content": "[]", "is_error": False}]},
    ]
    r = make(handler).complete(system="SYS", messages=msgs, tools=[TOOL])
    assert r.text == "hello" and not r.tool_calls
    m = seen["messages"]
    assert m[0] == {"role": "system", "content": "SYS"}
    assert m[2]["tool_calls"][0]["function"]["name"] == "search_products"
    assert m[3] == {"role": "tool", "tool_call_id": "t1", "content": "[]"}
    assert seen["tools"][0]["function"]["parameters"] == TOOL["input_schema"]


def test_tool_call_parsed():
    def handler(req):
        return httpx.Response(200, json={"choices": [{"message": {"content": None, "tool_calls": [
            {"id": "c1", "type": "function", "function": {"name": "search_products", "arguments": '{"q": "shirt"}'}}]}}]})

    r = make(handler).complete(system="s", messages=[{"role": "user", "content": "x"}], tools=[TOOL])
    assert r.tool_calls[0].name == "search_products" and r.tool_calls[0].input == {"q": "shirt"}


def test_forced_tool_falls_back_to_required():
    choices = []

    def handler(req):
        body = json.loads(req.content)
        choices.append(body["tool_choice"])
        if len(choices) == 1:
            return httpx.Response(400, json={"error": {"message": "tool_choice not supported"}})
        return httpx.Response(200, json={"choices": [{"message": {"tool_calls": [
            {"id": "c", "function": {"name": "search_products", "arguments": "{}"}}]}}]})

    r = make(handler).complete(system="s", messages=[{"role": "user", "content": "x"}], tools=[TOOL],
                               force_tool="search_products")
    assert choices[1] == "required" and r.tool_calls


def test_errors_map_to_llm_exceptions():
    with pytest.raises(LLMUnavailable):
        make(lambda req: httpx.Response(429)).complete(system="s", messages=[], tools=[])
    with pytest.raises(LLMError) as e:
        make(lambda req: httpx.Response(401, json={"error": {"message": "bad key"}})).complete(
            system="s", messages=[], tools=[])
    assert not isinstance(e.value, LLMUnavailable)


def test_build_llm_selection(monkeypatch):
    base = dict(_env_file=None)
    assert isinstance(build_llm(Settings(**base)), UnconfiguredLLM)
    assert isinstance(build_llm(Settings(llm_provider="groq", **base)), UnconfiguredLLM)
    assert isinstance(build_llm(Settings(llm_provider="groq", llm_api_key="k", **base)), OpenAICompatLLM)
    assert isinstance(build_llm(Settings(llm_provider="ollama", **base)), OpenAICompatLLM)
    assert isinstance(build_llm(Settings(llm_provider="nonsense", **base)), UnconfiguredLLM)
