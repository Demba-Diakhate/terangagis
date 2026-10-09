"""Smoke de la memoire de conversation du panneau (S13) avec des doublures.

Usage :
    <python QGIS> tests/conversation_smoke.py
"""
import time

from plugin.agent.agent import AgentPlan, AgentStep


class _StubAgent:
    def __init__(self):
        self.seen = []

    def plan(self, instruction, context='', conversation=None):
        self.seen.append(list(conversation.messages()) if conversation is not None else [])
        return AgentPlan(steps=[AgentStep(tool='get_project_info', params={})], assistant_text='ok')


class _StubOrch:
    def run(self, plan, **kwargs):
        from plugin.agent.orchestrator import ExecutionReport
        return None, ExecutionReport(steps=[])


def _wait(app, panel, needle):
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

    panel.input.setText("informations sur la ville")
    panel.submit()
    _wait(app, panel, 'Terminé.')

    panel.input.setText("et maintenant ?")
    panel.submit()
    _wait(app, panel, 'Terminé.')

    failures = []

    def check(name, cond, detail=''):
        print(f"PASS {name}" if cond else f"FAIL {name} - {detail}")
        if not cond:
            failures.append(name)

    check('deux_plans', len(agent.seen) == 2, agent.seen)
    check('premier_sans_contexte', agent.seen[0] == [], agent.seen[0])
    check(
        'second_avec_contexte',
        any(t.get('role') == 'user' and 'informations' in t.get('content', '') for t in agent.seen[1]),
        agent.seen[1],
    )
    check('conversation_non_vide', len(panel.conversation) >= 2, len(panel.conversation))

    return 0 if not failures else 1


if __name__ == '__main__':
    import sys
    sys.exit(main())
