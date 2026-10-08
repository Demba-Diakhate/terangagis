"""Smoke du panneau de chat (flux soumission -> plan -> exécution) avec des doublures.

Usage :
    "C:/Program Files/QGIS 3.44.15/bin/python-qgis-ltr.bat" tests/chat_panel_smoke.py
"""
import time

from mcp.bridge_client import BridgeClient  # noqa: F401  (vérifie import sans QGIS)
from plugin.agent.agent import AgentPlan, AgentStep


class _StubAgent:
    def plan(self, instruction):
        return AgentPlan(
            steps=[AgentStep(tool='get_project_info', params={})],
            assistant_text='Je liste les informations du projet.',
        )


class _StubOrch:
    def run(self, plan, **kwargs):
        from plugin.agent.orchestrator import ExecutionReport, StepResult
        from plugin.agent.validation import ValidationReport
        result = {'ok': True, 'data': {'project_name': 'demo'}}
        return ValidationReport(), ExecutionReport(steps=[StepResult('get_project_info', {}, True, result)])


def main() -> int:
    try:
        from qgis.PyQt.QtWidgets import QApplication
    except ImportError:
        print("SKIP: qgis non importable (lancer avec python-qgis-ltr.bat)")
        return 0

    app = QApplication.instance() or QApplication([])
    from plugin.ui.chat_panel import ChatPanel

    panel = ChatPanel(_StubAgent(), _StubOrch())
    panel.input.setText("informations du projet")
    panel.submit()

    deadline = time.time() + 20
    while time.time() < deadline:
        app.processEvents()
        if 'Résultats' in panel.transcript.toPlainText():
            break
        time.sleep(0.01)

    text = panel.transcript.toPlainText()
    failures = []

    def check(name, cond, detail=''):
        print(f"{'PASS' if cond else 'FAIL'} {name}{(' — ' + str(detail)) if detail and not cond else ''}")
        if not cond:
            failures.append(name)

    check('plan_affiche', 'Plan :' in text)
    check('validation_affichee', 'Validation : OK.' in text)
    check('resultats_affiches', 'Résultats :' in text and 'get_project_info : OK' in text)
    check('pas_de_confirmation_en_lecture', 'Confirmation' not in panel.status.text())

    app.quit()
    return 1 if failures else 0


if __name__ == '__main__':
    raise SystemExit(main())