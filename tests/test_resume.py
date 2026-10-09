"""Tests de la reprise d'execution (S13). Purs, sans QGIS."""
from __future__ import annotations

from plugin.agent.agent import AgentPlan, AgentStep
from plugin.agent.orchestrator import ExecutionReport, Orchestrator, StepResult

_PARAMS = {
    'buffer': {'layer': 'L', 'distance': 1},
    'clip': {'layer': 'L', 'overlay': 'M'},
    'dissolve': {'layer': 'L'},
    'reproject_layer': {'layer': 'L', 'crs': 'EPSG:32628'},
}


class _Client:
    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = []
        self._last = {'ok': True, 'data': {}}

    def execute(self, tool, params):
        self.calls.append((tool, params))
        if self.responses:
            self._last = self.responses.pop(0)
        return self._last


def _step(tool):
    return AgentStep(tool=tool, params=dict(_params_for(tool)))


def _params_for(tool):
    return {'layer': 'L'} if tool != 'clip' else {'layer': 'L', 'overlay': 'M'}


def _plan(*tools):
    return AgentPlan(steps=[AgentStep(tool=t, params={'layer': 'L', 'distance': 1, 'layers': 'L'}) for t in tools])


def test_resume_reruns_failed_and_remaining():
    client = _Client([{'ok': True, 'data': {}}])
    orch = Orchestrator(client)
    plan = AgentPlan(steps=[
        AgentStep('buffer', {'layer': 'L', 'distance': 1}),
        AgentStep('dissolve', {'layer': 'L'}),
        AgentStep('dissolve', {'layer': 'L'}),
    ])
    previous = ExecutionReport(steps=[], failed_index=0)
    report, exec_report = orch.resume(plan, previous, max_retries=0, sleep=lambda _: None)
    assert [c[0] for c in client.calls] == ['buffer', 'dissolve', 'dissolve']
    assert exec_report.ok


def test_resume_starts_at_failed_index():
    client = _Client([{'ok': True, 'data': {}}])
    orch = Orchestrator(client)
    plan = AgentPlan(steps=[
        AgentStep('dissolve', {'layer': 'L'}),
        AgentStep('buffer', {'layer': 'L', 'distance': 10}),
    ])
    previous = ExecutionReport(steps=[], failed_index=1)
    _, exec_report = orch.resume(plan, previous, max_retries=0, sleep=lambda _: None)
    assert [c[0] for c in client.calls] == ['buffer']
    assert exec_report.ok


def test_resume_with_plan_override_replaces_failed_part():
    client = _Client([{'ok': True, 'data': {}}])
    orch = Orchestrator(client)
    plan = _plan('dissolve', 'clip')
    previous = ExecutionReport(steps=[], failed_index=0)
    fixed = AgentPlan(steps=[_step('dissolve')])
    _, exec_report = orch.resume(plan, previous, plan_override=fixed, max_retries=0, sleep=lambda _: None)
    assert [c[0] for c in client.calls] == ['dissolve']
    assert exec_report.ok
