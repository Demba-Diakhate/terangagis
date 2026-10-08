import json

import pytest

from common.config import Settings
from plugin.agent.agent import AgentError, GeoAgent
from plugin.agent.llm import LLMClient, LLMError
from plugin.agent.tools_schema import openai_tools


def _settings(key="k"):
    return Settings(
        provider="openrouter",
        base_url="https://example.test/v1",
        api_key=key,
        model="test-model",
        max_retries=1,
        timeout=5,
    )


def test_openai_tools_has_16():
    tools = openai_tools()
    assert len(tools) == 16
    assert all(t["type"] == "function" for t in tools)
    names = {t["function"]["name"] for t in tools}
    assert "buffer" in names


def test_llm_requires_key():
    client = LLMClient(settings=_settings(""), transport=lambda *a: {})
    assert client.ready is False
    with pytest.raises(LLMError):
        client.chat([{"role": "user", "content": "salut"}])


def test_llm_extracts_message():
    captured = {}

    def transport(url, headers, body, timeout):
        captured["url"] = url
        captured["headers"] = headers
        captured["payload"] = json.loads(body)
        return {"choices": [{"message": {"role": "assistant", "content": "ok"}}]}

    client = LLMClient(settings=_settings(), transport=transport)
    msg = client.chat([{"role": "user", "content": "salut"}])
    assert msg["content"] == "ok"
    assert captured["url"].endswith("/chat/completions")
    assert captured["headers"]["Authorization"] == "Bearer k"


def test_llm_retries_then_succeeds():
    calls = {"n": 0}

    def transport(url, headers, body, timeout):
        calls["n"] += 1
        if calls["n"] == 1:
            raise LLMError("boom")
        return {"choices": [{"message": {"role": "assistant", "content": "ok"}}]}

    client = LLMClient(settings=_settings(), transport=transport)
    assert client.chat([{"role": "user", "content": "x"}])["content"] == "ok"
    assert calls["n"] == 2


def test_agent_plan_parses_tool_calls():
    def transport(url, headers, body, timeout):
        return {"choices": [{"message": {
            "role": "assistant",
            "content": "Je crée un tampon.",
            "tool_calls": [
                {"id": "1", "type": "function", "function": {"name": "buffer", "arguments": json.dumps({"layer": "L", "distance": 100})}},
            ],
        }}]}

    agent = GeoAgent(llm=LLMClient(settings=_settings(), transport=transport))
    plan = agent.plan("Fais un buffer de 100 m sur L")
    assert len(plan.steps) == 1
    assert plan.steps[0].tool == "buffer"
    assert plan.steps[0].params == {"layer": "L", "distance": 100}
    assert "tampon" in plan.assistant_text


def test_agent_empty_query_raises():
    agent = GeoAgent(llm=LLMClient(settings=_settings(), transport=lambda *a: {}))
    with pytest.raises(AgentError):
        agent.plan("   ")


def test_agent_rejects_non_object_arguments():
    def transport(url, headers, body, timeout):
        return {"choices": [{"message": {
            "role": "assistant",
            "content": "",
            "tool_calls": [{"id": "1", "type": "function", "function": {"name": "buffer", "arguments": "not-json"}}],
        }}]}

    agent = GeoAgent(llm=LLMClient(settings=_settings(), transport=transport))
    with pytest.raises(AgentError):
        agent.plan("buffer")