"""Tests du contrôle d'exécution (progression + annulation) de l'orchestrateur (S14). Purs."""
from __future__ import annotations

from plugin.agent.agent import AgentPlan, AgentStep
from plugin.agent.orchestrator import Orchestrator


class _Client:
    def __init__(self, responses=None):
        self.responses = list(responses or [])
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


def test_step_callbacks_report_progress_in_order():
    client = _Client()
    starts, finishes = [], []
    orch = Orchestrator(client)
    plan = _plan(_step('buffer'), _step('dissolve'))
    _, report = orch.run(
        plan,
        on_step_start=lambda i, s: starts.append((i, s.tool)),
        on_step_finished=lambda i, r: finishes.append((i, r.tool)),
    )
    assert report.ok
    assert starts == [(0, 'buffer'), (1, 'dissolve')]
    assert finishes == [(0, 'buffer'), (1, 'dissolve')]


def test_cancel_before_first_step_skips_all():
    client = _Client()
    orch = Orchestrator(client)
    _, report = orch.run(_plan(_step()), should_cancel=lambda: True)
    assert report.cancelled is True
    assert report.steps == []
    assert client.calls == []


def test_cancel_between_steps_stops_remaining():
    client = _Client()
    state = {'cancel': False}

    def should_cancel():
        return state['cancel']

    def on_finished(index, result):
        if index == 0:
            flag['set'] = True

    orch = Orchestrator(client)
    plan = _plan(_step('buffer'), _step('dissolve'))
    # annule après la première étape via on_step_finished
    _, report = orch.run(
        plan,
        should_cancel=lambda: state['cancel'],
        on_step_finished=lambda i, r: state.__setitem__('cancel', True),
    )
    assert report.cancelled is True
    assert len(report.steps) == 1
    assert report.steps[0].tool == 'buffer'
    assert [c[0] for c in client.calls] == ['buffer']
    assert report.failed_index is None


def test_not_cancelled_by_default():
    client = _Client()
    orch = Orchestrator(client)
    _, report = orch.run(_plan(_step()))
    assert report.cancelled is False
    assert report.ok


def test_cancel_between_retries_stops_retrying():
    client = _Client([{'ok': False, 'error': {'code': 'tool_exception'}}])
    orch = Orchestrator(client)
    calls = {'n': 0}

    def should_cancel():
        calls['n'] += 1
        return calls['n'] > 1

    _, report = orch.run(
        _plan(_step()),
        max_retries=3,
        backoff_base=0.0,
        sleep=lambda _: None,
        should_cancel=should_cancel,
    )
    assert not report.steps[0].ok
    assert report.steps[0].attempts == 1
    assert len(client.calls) == 1
    assert report.cancelled is False
