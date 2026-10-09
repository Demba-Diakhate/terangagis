"""Smoke du flux de correction (reprise + repair 1 essai) du panneau (S13).

Usage :
    <python QGIS> tests/recovery_smoke.py
"""
import time

from plugin.agent.agent import AgentPlan, AgentStep


class _StubAgent:
    def __init__(self):
        self.repairs = 0

    def plan(self, instruction, context='', conversation=None):
        return AgentPlan(
            steps=[AgentStep(tool='buffer', params={'layer': 'routes', 'distance': 500})],
            assistant_text='tampon',
        )

    def repair(self, failed_step, error_message, context=''):
        self.repairs += 1
        return AgentPlan(steps=[AgentStep(tool='dissolve', params={'layer': 'routes'})], assistant_text='corrige')


class _StubOrch:
    def __init__(self):
        self.calls = 0

    def run(self, plan, **kwargs):
        from plugin.agent.orchestrator import ExecutionReport, StepResult
        from plugin.agent.validation import ValidationReport
        self.calls += 1
        if self.calls == 1:
            result = {'ok': False, 'error': {'code': 'internal', 'message': 'transitoire'}}
            return ValidationReport(), ExecutionReport(
                steps=[StepResult('buffer', {}, False, result, 3, 'transient')],
                stopped_on_error=True,
                failed_index=0,
            )
        result = {'ok': True, 'data': {}}
        return ValidationReport(), ExecutionReport(steps=[StepResult('dissolve', {}, True, result)])


def main() -> int:
    try:
        from qgis.PyQt.QtWidgets import QApplication
    except ImportError:
        print("SKIP: qgis non importable")
        return 0

    app = QApplication.instance() or QApplication([])
    from plugin.ui.chat_panel import ChatPanel

    agent = _StubAgent()
    panel = ChatPanel(agent, _StubOrch())
    panel._confirm_repair = lambda step: True
    panel._confirm = lambda plan: True

    panel.input.setText("tampon des routes")
    panel.submit()

    deadline = time.time() + 20
    while time.time() < deadline:
        app.processEvents()
        text = panel.transcript.toPlainText()
        if 'Correction proposée' in text and 'Terminé' in text:
            break
        time.sleep(0.01)

    failures = []

    def check(name, cond, detail=''):
        print(f"{'PASS' if cond else 'FAIL'} {name}" + (f" ({detail})" if not cond else ''))
        if not cond:
            failures.append(name)

    text = panel.transcript.toPlainText()
    check('correction_proposee', 'Correction proposée' in text)
    check('une_seule_fois', getattr(agent, 'repairs', 0) == 1, agent.repairs)
    check('reprise_reussie', 'Terminé.' in text, text[-200:])

    return 0 if not failures else 1


if __name__ == '__main__':
    raise SystemExit(main())
