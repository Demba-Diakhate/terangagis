"""Tests de la correction LLM d'une etape echouee (S13). Purs, sans QGIS."""
from __future__ import annotations

import json

import pytest

from common.config import Settings
from plugin.agent.agent import AgentError, AgentStep, GeoAgent
from plugin.agent.llm import LLMClient, LLMError


def _settings():
    return Settings(
        provider='openrouter',
        base_url='https://example.test/v1',
        api_key='k',
        model='m',
        max_retries=0,
        timeout=5,
        step_max_retries=1,
        llm_backoff=0.0,
    )


def _tool_call(name, arguments):
    return {
        'choices': [{'message': {'role': 'assistant', 'content': '', 'tool_calls': [
            {'id': '1', 'type': 'function', 'function': {'name': name, 'arguments': arguments}},
        ]}}]
    }


def test_repair_returns_corrected_plan():
    import json

    def transport(url, headers, body, timeout):
        return _tool_call('buffer', json.dumps({'layer': 'routes', 'distance': 100}))

    agent = GeoAgent(llm=LLMClient(settings=_settings(), transport=transport, sleep=lambda _: None))
    step = AgentStep(tool='buffer', params={'layer': 'routes', 'distance': -1})
    plan = agent.repair(step, 'distance invalide')
    assert len(plan.steps) == 1
    assert plan.steps[0].tool == 'buffer'
    assert plan.steps[0].params['distance'] == 100


def test_repair_propagates_llm_error_as_agent_error():
    from plugin.agent.llm import LLMError

    def transport(url, headers, body, timeout):
        raise LLMError('boom', retryable=False)

    agent = GeoAgent(llm=LLMClient(settings=_settings(), transport=transport, sleep=lambda _: None))
    with pytest.raises(AgentError):
        agent.repair(AgentStep(tool='buffer', params={}), 'boom')


def test_repair_invalid_response_raises_agent_error():
    def transport(url, headers, body, timeout):
        return _tool_call('outil_inconnu', '{}')

    agent = GeoAgent(llm=LLMClient(settings=_settings(), transport=transport, sleep=lambda _: None))
    with pytest.raises(AgentError):
        agent.repair(AgentStep(tool='buffer', params={}), 'erreur')
