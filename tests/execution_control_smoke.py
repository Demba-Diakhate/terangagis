"""Smoke du contrôle d'exécution (progression + annulation) du panneau chat (S14).

Usage :
    "C:/Program Files/QGIS 3.44.15/bin/python-qgis-ltr.bat" tests/execution_control_smoke.py
"""
import threading
import time

from plugin.agent.agent import AgentPlan, AgentStep


class _StubAgent:
    def plan(self, instruction, context='', conversation=None):
        return AgentPlan(
            steps=[AgentStep(tool='get_project_info', params={}),
                   AgentStep(tool='list_layers', params={})],
            assistant_text='ok',
        )


def _step_result(step):
    from plugin.agent.orchestrator import StepResult
    return StepResult(step.tool, step.params, True, {'ok': True, 'data': {}})


class _StubOrch:
    def run(self, plan, **kwargs):
        from plugin.agent.orchestrator import ExecutionReport
        from plugin.agent.validation import ValidationReport
        on_start = kwargs.get('on_step_start')
        report = ExecutionReport()
        for index, step in enumerate(plan.steps):
            if on_start is not None:
                on_start(index, step)
            report.steps.append(_step_result(step))
        return ValidationReport(), report


class _GateOrch:
    """Bloque à la 1re étape pour laisser l'utilisateur annuler, puis honore `should_cancel`."""

    def __init__(self):
        self.gate = threading.Event()
        self.entered = threading.Event()

    def run(self, plan, **kwargs):
        from plugin.agent.orchestrator import ExecutionReport
        from plugin.agent.validation import ValidationReport
        on_start = kwargs.get('on_step_start')
        should_cancel = kwargs.get('should_cancel')
        report = ExecutionReport()
        for index, step in enumerate(plan.steps):
            if index == 0:
                self.entered.set()
                self.gate.wait(timeout=10)
            if should_cancel is not None and should_cancel():
                report.cancelled = True
                report.stopped_on_error = True
                return ValidationReport(), report
            if on_start is not None:
                on_start(index, step)
            report.steps.append(_step_result(step))
        return ValidationReport(), report


def _wait(app, predicate, timeout=20.0):
    deadline = time.time() + timeout
    while time.time() < deadline:
        app.processEvents()
        if predicate():
            return True
        time.sleep(0.01)
    return False


def main() -> int:
    try:
        from qgis.PyQt.QtWidgets import QApplication
    except ImportError:
        print("SKIP: qgis non importable (lancer avec python-qgis-ltr.bat)")
        return 0

    app = QApplication.instance() or QApplication([])
    from plugin.ui.chat_panel import ChatPanel

    failures = []

    def check(name, cond, detail=''):
        print(f"{'PASS' if cond else 'FAIL'} {name}{(' — ' + str(detail)) if detail and not cond else ''}")
        if not cond:
            failures.append(name)

    # Scénario 1 : progression normale affichée et journalisée.
    panel1 = ChatPanel(_StubAgent(), _StubOrch())
    panel1.input.setText("informations du projet")
    panel1.submit()
    _wait_panel(panel1, 'Résultats')

    check('progression_journalisee',
          panel1.progress_log == [(0, 2, 'get_project_info'), (1, 2, 'list_layers')],
          panel1.progress_log)
    check('progression_totale', all(total == 2 for _, total, _ in panel1.progress_log), panel1.progress_log)
    check('execution_terminee', 'Terminé.' in panel1.transcript.toPlainText())

    # Scénario 2 : annulation pendant l'exécution.
    gate_orch = _GateOrch()
    panel2 = ChatPanel(_StubAgent(), gate_orch)
    panel2.input.setText("informations du projet")
    panel2.submit()
    # L'orchestrateur est bloqué à la 1re étape : le bouton Annuler doit être actif.
    _wait(app, gate_orch.entered.is_set)
    check('annulation_disponible', panel2.cancel_button.isEnabled())
    panel2.cancel()
    gate_orch.gate.set()
    _wait(app, lambda: 'annulée' in panel2.transcript.toPlainText())
    check('annulation_effective', 'Exécution annulée.' in panel2.transcript.toPlainText())

    app.quit()
    return 1 if failures else 0


def _wait_panel(panel, needle, timeout=20.0):
    from qgis.PyQt.QtWidgets import QApplication
    app = QApplication.instance()
    deadline = time.time() + timeout
    while time.time() < deadline:
        app.processEvents()
        if needle in panel.transcript.toPlainText():
            return True
        time.sleep(0.01)
    return False


if __name__ == '__main__':
    raise SystemExit(main())
