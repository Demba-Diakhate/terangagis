"""Exécution batch d'instructions (S21 — V4 finalisation)."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from plugin.agent.agent import AgentPlan, GeoAgent, AgentError
from plugin.agent.orchestrator import ExecutionReport, Orchestrator


@dataclass
class BatchItem:
    instruction: str
    plan: AgentPlan = field(default_factory=AgentPlan)
    exec_report: ExecutionReport = field(default_factory=ExecutionReport)
    ok: bool = True
    error: Optional[str] = None


@dataclass
class BatchResult:
    items: List[BatchItem] = field(default_factory=list)
    ok: bool = True

    @property
    def summary(self) -> str:
        total = len(self.items)
        success = sum(1 for i in self.items if i.ok and i.exec_report.ok)
        failed = total - success
        return f"batch: {success}/{total} réussis, {failed} échecs"


class BatchRunner:
    def __init__(self, agent: GeoAgent, orchestrator: Orchestrator) -> None:
        self.agent = agent
        self.orchestrator = orchestrator

    def run(self, instructions: List[str], **kwargs: Any) -> BatchResult:
        res = BatchResult(ok=True)
        for instr in instructions:
            item = BatchItem(instruction=instr)
            try:
                plan = self.agent.plan(instr)
                item.plan = plan
                report, exec_report = self.orchestrator.run(plan, **kwargs)
                item.exec_report = exec_report
                item.ok = exec_report.ok
                if not exec_report.ok:
                    res.ok = False
            except Exception as e:
                item.ok = False
                item.error = str(e)
                res.ok = False
            res.items.append(item)
        return res
