"""Tests de l'exécution robuste de l'orchestrateur (S12). Purs, sans QGIS."""
from __future__ import annotations

from plugin.agent.agent import AgentPlan, AgentStep
from plugin.agent.orchestrator import Orchestrator


class _SeqClient:
    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = []
        self._last = {'ok': True, 'data': {}}

    def execute(self, tool, params):
        self.calls.append((tool, params))
        if self.responses:
            self._last = self.responses.pop(0)
        return self._last


def _plan(*steps):
    return AgentPlan(steps=list(steps))


def _step(tool='buffer', params=None, **kwargs):
    return AgentStep(tool=tool, params=params or {'layer': 'L', 'distance': 1}, **kwargs)


def test_transient_error_is_retried_then_succeeds():
    client = _SeqClient([
        {'ok': False, 'error': {'code': 'tool_exception'}},
        {'ok': True, 'data': {'output': 'x.gpkg'}},
    ])
    sleeps = []
    orch = Orchestrator(client)
    _, report = orch.run(_plan(_step()), max_retries=1, backoff_base=0.0, sleep=sleeps.append)
    assert report.ok
    assert report.steps[0].attempts == 2
    assert len(client.calls) == 2
    assert sleeps == [0.0]


def test_permanent_error_is_not_retried():
    client = _SeqClient([{'ok': False, 'error': {'code': 'layer_not_found'}}])
    orch = Orchestrator(client)
    _, report = orch.run(_plan(_step()), max_retries=3, sleep=lambda _: None)
    assert not report.ok
    assert report.steps[0].attempts == 1
    assert report.steps[0].error_class == 'permanent'
    assert report.recoverable is False
    assert len(client.calls) == 1


def test_transient_exhausted_is_recoverable():
    client = _SeqClient([{'ok': False, 'error': {'code': 'internal'}}])
    orch = Orchestrator(client)
    _, report = orch.run(_plan(_step()), max_retries=2, backoff_base=0.0, sleep=lambda _: None)
    assert not report.ok
    assert report.steps[0].attempts == 3
    assert report.stopped_on_error is True
    assert report.failed_index == 0
    assert report.recoverable is True
    assert len(client.calls) == 3


def test_on_error_continue_executes_next_step():
    client = _SeqClient([
        {'ok': False, 'error': {'code': 'missing_param'}},
        {'ok': True, 'data': {}},
    ])
    orch = Orchestrator(client)
    plan = _plan(_step('buffer'), _step('dissolve'))
    _, report = orch.run(plan, on_error='continue', max_retries=0)
    assert len(report.steps) == 2
    assert report.failed_index == 0
    assert report.stopped_on_error is False
    assert [c[0] for c in client.calls] == ['buffer', 'dissolve']


def test_step_override_disables_retry():
    client = _SeqClient([
        {'ok': False, 'error': {'code': 'tool_exception'}},
        {'ok': True, 'data': {}},
    ])
    orch = Orchestrator(client)
    _, report = orch.run(_plan(_step(max_retries=0)), max_retries=3, sleep=lambda _: None)
    assert not report.ok
    assert report.steps[0].attempts == 1
    assert len(client.calls) == 1


def test_step_override_enables_retry():
    client = _SeqClient([
        {'ok': False, 'error': {'code': 'tool_exception'}},
        {'ok': True, 'data': {}},
    ])
    orch = Orchestrator(client)
    _, report = orch.run(_plan(_step(max_retries=1)), max_retries=0, backoff_base=0.0, sleep=lambda _: None)
    assert report.ok
    assert report.steps[0].attempts == 2


def test_failed_step_is_exposed():
    client = _SeqClient([{'ok': False, 'error': {'code': 'bad_distance'}}])
    orch = Orchestrator(client)
    plan = _plan(_step('buffer', {'layer': 'L', 'distance': 1}))
    _, report = orch.run(plan, max_retries=2, sleep=lambda _: None)
    assert report.failed_step is not None
    assert report.failed_step.tool == 'buffer'
    assert report.failed_step.error_class == 'permanent'
    assert report.recoverable is False
