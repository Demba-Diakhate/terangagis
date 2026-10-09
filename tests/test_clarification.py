"""Tests des questions de clarification de l'agent (S15). Purs, sans QGIS."""
import json

import pytest

from common.config import Settings
from plugin.agent.agent import AgentError, GeoAgent
from plugin.agent.llm import LLMClient
from plugin.agent.tools_schema import CLARIFICATION_TOOL_NAME, clarification_tool, openai_tools


def _settings(key="k"):
    return Settings(
        provider="openrouter",
        base_url="https://example.test/v1",
        api_key=key,
        model="test-model",
        max_retries=1,
        timeout=5,
    )


def _message(tool_calls):
    return {"choices": [{"message": {
        "role": "assistant", "content": "ok", "tool_calls": tool_calls,
    }}]}


def _call(name, arguments):
    return {"id": "1", "type": "function",
            "function": {"name": name, "arguments": json.dumps(arguments)}}


def test_clarification_tool_defaults_off():
    assert len(openai_tools()) == 16
    tools = openai_tools(include_clarification=True)
    names = {t["function"]["name"] for t in tools}
    assert len(tools) == 17
    assert CLARIFICATION_TOOL_NAME in names
    assert clarification_tool()["function"]["parameters"]["required"] == ["question"]


def test_agent_plan_parses_clarification():
    def transport(url, headers, body, timeout):
        return _message([_call(CLARIFICATION_TOOL_NAME, {"question": "Quelle couche ?"})])

    agent = GeoAgent(llm=LLMClient(settings=_settings(), transport=transport))
    plan = agent.plan("Fais un buffer de 5 km")
    assert plan.steps == []
    assert plan.clarification == "Quelle couche ?"


def test_clarification_takes_precedence_over_steps():
    def transport(url, headers, body, timeout):
        return _message([
            {"id": "1", "type": "function", "function": {"name": "buffer", "arguments": json.dumps({"layer": "L", "distance": 5})}},
            {"id": "2", "type": "function", "function": {"name": CLARIFICATION_TOOL_NAME, "arguments": json.dumps({"question": "Quelle distance ?"})}},
        ])

    agent = GeoAgent(llm=LLMClient(settings=_settings(), transport=transport))
    plan = agent.plan("buffer")
    assert plan.clarification == "Quelle distance ?"
    assert plan.steps == []


def test_clarification_requires_question():
    def transport(url, headers, body, timeout):
        return _message([{"id": "1", "type": "function", "function": {"name": CLARIFICATION_TOOL_NAME, "arguments": "{}"}}])

    agent = GeoAgent(llm=LLMClient(settings=_settings(), transport=transport))
    with pytest.raises(AgentError):
        agent.plan("buffer")


def test_clarification_tool_is_not_an_mcp_tool():
    from plugin.agent.tools_schema import TOOL_NAMES

    assert CLARIFICATION_TOOL_NAME not in TOOL_NAMES
    assert clarification_tool()["function"]["name"] == CLARIFICATION_TOOL_NAME


def test_normal_plan_has_no_clarification():
    def transport(url, headers, body, timeout):
        return _message([{"id": "1", "type": "function", "function": {"name": "list_layers", "arguments": "{}"}}])

    agent = GeoAgent(llm=LLMClient(settings=_settings(), transport=transport))
    plan = agent.plan("liste les couches")
    assert plan.clarification is None
    assert len(plan.steps) == 1
    assert plan.steps[0].tool == "list_layers"
