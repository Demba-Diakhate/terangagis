"""Smoke des questions de clarification du panneau (S15) avec des doublures.

Usage :
    <python QGIS> tests/clarification_smoke.py
"""
import time

from plugin.agent.agent import AgentPlan, AgentStep


class _StubAgent:
    def __init__(self):
        self.seen = []

    def plan(self, instruction, context='', conversation=None):
        self.seen.append(list(conversation.messages()) if conversation is not None else [])
        if len(self.seen) == 1:
            return AgentPlan(clarification="Quelle couche faut-il utiliser ?", assistant_text='')
        return AgentPlan(steps=[AgentStep(tool='get_project_info', params={})], assistant_text='ok')


class _StubOrch:
    def run(self, plan, **kwargs):
        from plugin.agent.orchestrator import ExecutionReport
        return None, ExecutionReport(steps=[])


def _wait(app, panel, needle):
    import time as _t
    deadline = time.time() + 20
    while time.time() < deadline:
        app.processEvents()
        worker = getattr(panel, '_worker', None)
        busy = worker is not None and worker.isRunning()
        if needle in panel.transcript.toPlainText() and not busy:
            break
        time.sleep(0.01)


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

    panel.input.setText("fais un tampon")
    panel.submit()
    _wait(app, panel, 'Question :')

    panel.input.setText("la couche routes")
    panel.submit()
    _wait(app, panel, 'Terminé.')

    failures = []

    def check(name, cond, detail=''):
        print(f"PASS {name}" if cond else f"FAIL {name} - {detail}")
        if not cond:
            failures.append(name)

    text = panel.transcript.toPlainText()
    check('question_posee', 'Question :' in text, text)
    check('clarification_journalisee', any(
        t.get('role') == 'assistant' and 'routes' not in t.get('content', '')
        for t in panel.conversation.messages()
    ), panel.conversation.messages())
    check('reponse_en_contexte', any(
        'routes' in t.get('content', '') for t in agent.seen[-1]
    ), agent.seen[-1])

    return 0 if not failures else 1


if __name__ == '__main__':
    import sys
    sys.exit(main())
