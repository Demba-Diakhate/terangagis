"""Orchestrateur d'exécution d'un plan (S05).

Valide (dry-run RT3) puis exécute séquentiellement les étapes via un client
(BridgeClient). S'arrête à la première erreur par défaut.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Protocol

from .agent import AgentPlan
from .journal import Journal
from .validation import ValidationReport, validate_plan


class ToolClient(Protocol):
    def execute(self, tool: str, params: dict | None = None) -> Dict[str, Any]: ...


@dataclass
class StepResult:
    tool: str
    params: Dict[str, Any]
    ok: bool
    result: Dict[str, Any] | None = None

    def to_dict(self) -> Dict[str, Any]:
        return {'tool': self.tool, 'params': self.params, 'ok': self.ok, 'result': self.result}


@dataclass
class ExecutionReport:
    steps: List[StepResult] = field(default_factory=list)
    stopped_on_error: bool = False

    @property
    def ok(self) -> bool:
        return all(s.ok for s in self.steps)


class Orchestrator:
    def __init__(self, client: ToolClient, journal: Journal | None = None) -> None:
        self.client = client
        self.journal = journal

    def run(
        self,
        plan: AgentPlan,
        *,
        dry_run: bool = False,
        layer_crs: Dict[str, str] | None = None,
        protected_sources: List[str] | None = None,
        on_confirm: Callable[[int, Any], bool] | None = None,
        stop_on_error: bool = True,
    ) -> tuple[ValidationReport, ExecutionReport]:
        report = validate_plan(plan, layer_crs=layer_crs, protected_sources=protected_sources)
        if self.journal:
            self.journal.record_validation(report)
        if dry_run:
            return report, ExecutionReport()
        if not report.ok:
            return report, ExecutionReport()

        exec_report = ExecutionReport()
        for index, step in enumerate(plan.steps):
            if on_confirm is not None and not on_confirm(index, step):
                exec_report.stopped_on_error = True
                break
            try:
                result = self.client.execute(step.tool, step.params)
                ok = bool(result.get('ok'))
            except Exception as e:  # noqa: BLE001
                result = {'ok': False, 'error': {'code': 'client_error', 'message': str(e)}}
                ok = False
            exec_report.steps.append(StepResult(step.tool, step.params, ok, result))
            if self.journal:
                self.journal.record_execution(step.tool, step.params, result)
            if not ok and stop_on_error:
                exec_report.stopped_on_error = True
                break
        return report, exec_report