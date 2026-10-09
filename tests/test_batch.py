"""Tests batch (S20)."""
from __future__ import annotations

from plugin.batch import BatchRunner


class DummyAgent:
    def __init__(self):
        pass
    def plan(self, instr):
        from plugin.agent.agent import AgentPlan, AgentStep
        return AgentPlan(steps=[AgentStep(tool='get_project_info', params={})])


class DummyOrch:
    def run(self, plan, **kwargs):
        from plugin.agent.orchestrator import ExecutionReport
        return (None, ExecutionReport())


def test_batch_runs():
    br = BatchRunner(DummyAgent(), DummyOrch())
    r = br.run(['a', 'b'])
    assert len(r.results) == 2
    assert r.ok
