"""Tests de la memoire de conversation (S13). Purs, sans QGIS."""
from __future__ import annotations

from plugin.agent.agent import AgentPlan, AgentStep
from plugin.agent.orchestrator import ExecutionReport, StepResult


def _step(tool, ok=True, artifact=None):
    result = {'ok': ok, 'data': ({'artifact': artifact} if artifact else {})}
    return StepResult(tool, {}, ok, result, 1, '' if ok else 'permanent')


def test_append_keeps_order_and_roles():
    from plugin.agent.conversation import Conversation

    conv = Conversation()
    conv.add_user('liste les couches')
    conv.add_assistant('ok')
    msgs = conv.messages()
    assert [m['role'] for m in msgs] == ['user', 'assistant']
    assert [m['content'] for m in msgs] == ['liste les couches', 'ok']


def test_add_plan_summarizes_tools():
    from plugin.agent.conversation import Conversation

    conv = Conversation()
    conv.add_plan(AgentPlan(steps=[AgentStep('buffer', {}), AgentStep('clip', {})], assistant_text=''))
    content = conv.messages()[0]['content']
    assert 'buffer' in content and 'clip' in content


def test_add_execution_collects_artifacts():
    from plugin.agent.conversation import Conversation

    conv = Conversation()
    report = ExecutionReport(steps=[_step('buffer', artifact='routes_buffer')])
    conv.add_execution(report)
    assert conv.artifacts == ['routes_buffer']
    assert 'routes_buffer' in conv.messages()[0]['content']


def test_failed_execution_is_summarized():
    from plugin.agent.conversation import Conversation

    conv = Conversation()
    report = ExecutionReport(steps=[_step('buffer', ok=False)], stopped_on_error=True, failed_index=0)
    conv.add_execution(report)
    assert 'buffer' in conv.messages()[0]['content']


def test_cancelled_execution_is_summarized():
    from plugin.agent.conversation import Conversation

    conv = Conversation()
    report = ExecutionReport(steps=[_step('buffer', artifact='routes_buffer')], cancelled=True)
    conv.add_execution(report)
    content = conv.messages()[0]['content']
    assert 'annulée' in content
    assert 'routes_buffer' in content


def test_budget_keeps_most_recent_turns():
    from plugin.agent.conversation import Conversation

    conv = Conversation(max_chars=6000, max_turns=3)
    for i in range(6):
        conv.add_user(f'tour {i}')
    msgs = conv.messages()
    assert [m['content'] for m in msgs] == ['tour 3', 'tour 4', 'tour 5']


def test_budget_limits_by_chars():
    from plugin.agent.conversation import Conversation

    conv = Conversation(max_chars=200, max_turns=12)
    for i in range(6):
        conv.add_user('x' * 100)
    assert len(conv.messages()) == 2


def test_clear_resets_state():
    from plugin.agent.conversation import Conversation

    conv = Conversation()
    conv.add_user('salut')
    conv.artifacts.append('a')
    conv.clear()
    assert len(conv) == 0
    assert conv.messages() == []
    assert conv.artifacts == []
