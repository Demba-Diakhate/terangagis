"""Orchestrateur d'exécution d'un plan (S05, durci en S12).

Valide (dry-run RT3) puis exécute séquentiellement les étapes via un client
(BridgeClient). Gère, par étape, la politique d'erreur (`stop`/`continue`) et un
nombre limité de retries avec backoff pour les erreurs **transitoires** (R3).
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Protocol

from .agent import AgentPlan, AgentStep
from .journal import Journal
from .retry import TRANSIENT, UNKNOWN, backoff_seconds, classify_error
from .validation import ValidationReport, validate_plan


class ToolClient(Protocol):
    def execute(self, tool: str, params: dict | None = None) -> Dict[str, Any]: ...


@dataclass
class StepResult:
    tool: str
    params: Dict[str, Any]
    ok: bool
    result: Dict[str, Any] | None = None
    attempts: int = 1
    error_class: str = ''

    def to_dict(self) -> Dict[str, Any]:
        return {
            'tool': self.tool,
            'params': self.params,
            'ok': self.ok,
            'result': self.result,
            'attempts': self.attempts,
            'error_class': self.error_class,
        }


@dataclass
class ExecutionReport:
    steps: List[StepResult] = field(default_factory=list)
    stopped_on_error: bool = False
    failed_index: Optional[int] = None
    cancelled: bool = False

    @property
    def ok(self) -> bool:
        return all(s.ok for s in self.steps)

    @property
    def failed_step(self) -> Optional[StepResult]:
        if self.failed_index is None:
            return None
        if 0 <= self.failed_index < len(self.steps):
            return self.steps[self.failed_index]
        return None

    @property
    def recoverable(self) -> bool:
        """Vrai si l'échec semble pouvoir être repris/corrigé (S13)."""
        step = self.failed_step
        if step is None or step.ok:
            return False
        return step.error_class in (TRANSIENT, UNKNOWN)


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
        on_error: str | None = None,
        max_retries: int = 1,
        backoff_base: float = 0.5,
        sleep: Callable[[float], None] | None = None,
        on_step_start: Callable[[int, AgentStep], None] | None = None,
        on_step_finished: Callable[[int, StepResult], None] | None = None,
        should_cancel: Callable[[], bool] | None = None,
    ) -> tuple[ValidationReport, ExecutionReport]:
        """Exécute le plan.

        - `on_error` : politique par défaut (`stop` | `continue`) ; `stop_on_error`
          est conservé pour compatibilité. Une étape peut surcharger via
          `AgentStep.on_error`.
        - `max_retries` : retries supplémentaires par étape pour une erreur
          transitoire (surchargeable via `AgentStep.max_retries`).
        - `on_step_start` / `on_step_finished` : notifications de progression (S14).
        - `should_cancel` : si fourni, vérifié **avant chaque étape** (et entre deux
          tentatives) ; s'il renvoie vrai, l'exécution s'arrête proprement et le
          rapport porte `cancelled=True`. L'annulation n'est pas instantanée au
          sein d'un algorithme de traitement.
        """
        report = validate_plan(plan, layer_crs=layer_crs, protected_sources=protected_sources)
        if self.journal:
            self.journal.record_validation(report)
        if dry_run:
            return report, ExecutionReport()
        if not report.ok:
            return report, ExecutionReport()

        default_policy = on_error or ('stop' if stop_on_error else 'continue')
        sleep_fn = sleep or time.sleep

        exec_report = ExecutionReport()
        for index, step in enumerate(plan.steps):
            if should_cancel is not None and should_cancel():
                exec_report.cancelled = True
                exec_report.stopped_on_error = True
                break

            if on_step_start is not None:
                on_step_start(index, step)

            if on_confirm is not None and not on_confirm(index, step):
                exec_report.stopped_on_error = True
                exec_report.failed_index = index
                break

            policy = step.on_error or default_policy
            step_retries = step.max_retries if step.max_retries is not None else max_retries
            max_attempts = max(1, 1 + int(step_retries))

            result, ok, attempts = self._run_step(
                step, max_attempts, backoff_base, sleep_fn, should_cancel,
            )
            error_class = '' if ok else classify_error((result or {}).get('error'))

            step_result = StepResult(step.tool, step.params, ok, result, attempts, error_class)
            exec_report.steps.append(step_result)
            if self.journal:
                self.journal.record_execution(
                    step.tool, step.params, result, attempts=attempts, error_class=error_class,
                )
            if on_step_finished is not None:
                on_step_finished(index, step_result)

            if not ok:
                exec_report.failed_index = index
                if policy != 'continue':
                    exec_report.stopped_on_error = True
                    break
        return report, exec_report

    def resume(
        self,
        plan: AgentPlan,
        previous_report: ExecutionReport,
        *,
        from_index: int | None = None,
        plan_override: AgentPlan | None = None,
        **kwargs: Any,
    ) -> tuple[ValidationReport, ExecutionReport]:
        """Reprend l'exécution à partir de l'étape qui a échoué (S13).

        Réexécute l'étape échouée et les suivantes (index de départ = par défaut
        `previous_report.failed_index`). `plan_override` permet de fournir un plan
        corrigé (proposé par le LLM) qui remplace les étapes restantes.
        """
        source = plan_override if plan_override is not None else plan
        start = from_index
        if start is None:
            start = previous_report.failed_index if previous_report.failed_index is not None else 0
        start = max(0, min(int(start), len(source.steps)))
        remaining = AgentPlan(steps=list(source.steps[start:]), assistant_text=source.assistant_text)
        return self.run(remaining, **kwargs)

    def _run_step(
        self,
        step: AgentStep,
        max_attempts: int,
        backoff_base: float,
        sleep_fn: Callable[[float], None],
        should_cancel: Callable[[], bool] | None = None,
    ) -> tuple[Dict[str, Any], bool, int]:
        attempt = 0
        result: Dict[str, Any] = {'ok': False, 'error': {'code': 'client_error', 'message': 'Échec inconnu'}}
        ok = False
        while attempt < max_attempts:
            attempt += 1
            try:
                result = self.client.execute(step.tool, step.params)
                ok = bool(result.get('ok'))
            except Exception as e:  # noqa: BLE001
                result = {'ok': False, 'error': {'code': 'client_error', 'message': str(e)}}
                ok = False
            if ok or attempt >= max_attempts:
                break
            if classify_error(result.get('error')) != TRANSIENT:
                break
            if should_cancel is not None and should_cancel():
                break
            sleep_fn(backoff_seconds(attempt, backoff_base))
        return result, ok, attempt
