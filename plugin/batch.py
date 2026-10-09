"""Exécution batch d'instructions (S20 — V4 Automation)."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from plugin.agent.agent import AgentPlan, GeoAgent, AgentError
from plugin.agent.orchestrator import ExecutionReport, Orchestrator


@dataclass
class BatchResult:
    results: List[tuple[str, AgentPlan, ExecutionReport]] = field(default_factory=list)
    ok: bool = True


class BatchRunner:
    def __init__(self, agent: GeoAgent, orchestrator: Orchestrator) -> None:
        self.agent = agent
        self.orchestrator = orchestrator

    def run(self, instructions: List[str], **kwargs: Any) -> BatchResult:
        res = BatchResult(ok=True)
        for instr in instructions:
            try:
                plan = self.agent.plan(instr)
                report, exec_report = self.orchestrator.run(plan, **kwargs)
                res.results.append((instr, plan, exec_report))
                if not exec_report.ok:
                    res.ok = False
            except Exception as e:
                # capture minimal
                res.ok = False
                res.results.append((instr, AgentPlan(), ExecutionReport()))
        return res
