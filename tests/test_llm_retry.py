"""Tests des retries LLM et de la reprise de parsing (S12). Purs, sans QGIS."""
from __future__ import annotations

import json

import pytest

from common.config import Settings
from plugin.agent.agent import AgentError, GeoAgent
from plugin.agent.llm import LLMClient, LLMError


def _settings(key="k", max_retries=2, backoff=0.5):
    return Settings(
        provider="openrouter",
        base_url="https://example.test/v1",
        api_key=key,
        model="test-model",
        max_retries=max_retries,
        timeout=5,
        step_max_retries=1,
        llm_backoff=backoff,
    )


def test_non_retryable_error_raises_immediately():
    calls = {"n": 0}

    def transport(url, headers, body, timeout):
        calls["n"] += 1
        raise LLMError("HTTP 400", retryable=False)

    client = LLMClient(settings=_settings(), transport=transport, sleep=lambda _: None)
    with pytest.raises(LLMError):
        client.chat([{"role": "user", "content": "x"}])
    assert calls["n"] == 1


def test_retryable_error_uses_backoff_and_succeeds():
    calls = {"n": 0}
    sleeps = []

    def transport(url, headers, body, timeout):
        calls["n"] += 1
        if calls["n"] < 3:
            raise LLMError("HTTP 503", retryable=True)
        return {"choices": [{"message": {"role": "assistant", "content": "ok"}}]}

    client = LLMClient(settings=_settings(max_retries=2, backoff=0.5), transport=transport, sleep=sleeps.append)
    msg = client.chat([{"role": "user", "content": "x"}])
    assert msg["content"] == "ok"
    assert calls["n"] == 3
    assert sleeps == [0.5, 1.0]


def test_retry_after_is_respected():
    calls = {"n": 0}
    sleeps = []

    def transport(url, headers, body, timeout):
        calls["n"] += 1
        if calls["n"] == 1:
            raise LLMError("HTTP 429", retryable=True, retry_after=7.0)
        return {"choices": [{"message": {"role": "assistant", "content": "ok"}}]}

    client = LLMClient(settings=_settings(max_retries=1), transport=transport, sleep=sleeps.append)
    client.chat([{"role": "user", "content": "x"}])
    assert sleeps == [7.0]


def test_agent_reparses_after_invalid_then_valid():
    calls = {"n": 0}

    def transport(url, headers, body, timeout):
        calls["n"] += 1
        if calls["n"] == 1:
            return {"choices": [{"message": {"role": "assistant", "content": "", "tool_calls": [
                {"id": "1", "type": "function", "function": {"name": "buffer", "arguments": "not-json"}},
            ]}}]}
        return {"choices": [{"message": {"role": "assistant", "content": "ok", "tool_calls": [
            {"id": "2", "type": "function", "function": {"name": "list_layers", "arguments": "{}"}},
        ]}}]}

    agent = GeoAgent(llm=LLMClient(settings=_settings(), transport=transport, sleep=lambda _: None), parse_retries=1)
    plan = agent.plan("liste les couches")
    assert calls["n"] == 2
    assert plan.steps[0].tool == "list_layers"


def test_agent_gives_up_after_parse_retries():
    calls = {"n": 0}

    def transport(url, headers, body, timeout):
        calls["n"] += 1
        return {"choices": [{"message": {"role": "assistant", "content": "", "tool_calls": [
            {"id": "1", "type": "function", "function": {"name": "buffer", "arguments": "not-json"}},
        ]}}]}

    agent = GeoAgent(llm=LLMClient(settings=_settings(), transport=transport, sleep=lambda _: None), parse_retries=1)
    with pytest.raises(AgentError):
        agent.plan("buffer")
    assert calls["n"] == 2
