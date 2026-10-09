"""Panneau de dialogue TerangaGIS (S06).

Interface en français : saisie d'instruction, affichage du plan, confirmation
des opérations risquées puis exécution via le bridge. Les appels (LLM, bridge)
tournent dans un thread worker pour ne pas bloquer QGIS (règle R6).
"""
from __future__ import annotations

from qgis.PyQt.QtCore import QThread, pyqtSignal
from qgis.PyQt.QtWidgets import (QHBoxLayout, QLabel, QMessageBox, QPlainTextEdit,
                                 QPushButton, QVBoxLayout, QWidget)

from plugin.agent.policy import requires_confirmation, risky_steps
from plugin.agent.validation import validate_plan
from plugin.ui.formatting import format_execution, format_plan, format_validation


class _PlanWorker(QThread):
    plan_ready = pyqtSignal(object)
    failed = pyqtSignal(str)

    def __init__(self, agent, instruction: str, context: str = '') -> None:
        super().__init__()
        self.agent = agent
        self.instruction = instruction
        self.context = context

    def run(self) -> None:  # noqa: D401
        try:
            plan = self.agent.plan(self.instruction, context=self.context)
        except Exception as e:  # noqa: BLE001
            self.failed.emit(str(e))
            return
        self.plan_ready.emit(plan)


class _ExecWorker(QThread):
    finished_report = pyqtSignal(object, object)
    failed = pyqtSignal(str)

    def __init__(self, orchestrator, plan, layer_crs=None, protected_sources=None, options=None) -> None:
        super().__init__()
        self.orchestrator = orchestrator
        self.plan = plan
        self.layer_crs = layer_crs
        self.protected_sources = protected_sources
        self.options = dict(options or {})

    def run(self) -> None:  # noqa: D401
        try:
            report, exec_report = self.orchestrator.run(
                self.plan,
                layer_crs=self.layer_crs,
                protected_sources=self.protected_sources,
                **self.options,
            )
        except Exception as e:  # noqa: BLE001
            self.failed.emit(str(e))
            return
        self.finished_report.emit(report, exec_report)


class ChatPanel(QWidget):
    def __init__(self, agent, orchestrator, context_provider=None, parent=None) -> None:
        super().__init__(parent)
        self.agent = agent
        self.orchestrator = orchestrator
        self.context_provider = context_provider
        self._plan = None
        self._worker = None
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)

        self.transcript = QPlainTextEdit()
        self.transcript.setReadOnly(True)
        self.transcript.setPlaceholderText("La conversation apparaîtra ici.")
        layout.addWidget(self.transcript)

        row = QHBoxLayout()
        from qgis.PyQt.QtWidgets import QLineEdit
        self.input = QLineEdit()
        self.input.setPlaceholderText("Ex. : fais un tampon de 500 m autour des routes")
        self.input.returnPressed.connect(self.submit)
        row.addWidget(self.input)

        self.send_button = QPushButton("Envoyer")
        self.send_button.clicked.connect(self.submit)
        row.addWidget(self.send_button)
        layout.addLayout(row)

        self.status = QLabel("Prêt.")
        layout.addWidget(self.status)

    def _append(self, text: str) -> None:
        self.transcript.appendPlainText(text)

    def submit(self) -> None:
        instruction = self.input.text().strip()
        if not instruction:
            return
        if self._worker is not None and self._worker.isRunning():
            return
        self.input.clear()
        self.send_button.setEnabled(False)
        self._append(f"Vous : {instruction}")
        self.status.setText("Analyse de la demande…")

        context = ''
        provider = getattr(self, 'context_provider', None)
        if callable(provider):
            try:
                context = provider() or ''
            except Exception:  # noqa: BLE001
                context = ''

        self._worker = _PlanWorker(self.agent, instruction, context)
        self._worker.plan_ready.connect(self._on_plan)
        self._worker.failed.connect(self._on_failed)
        self._worker.start()

    def _on_plan(self, plan) -> None:
        self._append(format_plan(plan))
        if not plan.steps:
            self._append("Aucune action à exécuter.")
            self._reset()
            return

        layer_crs = None
        getter = getattr(self, '_layer_crs_provider', None)
        if callable(getter):
            try:
                layer_crs = getter()
            except Exception:  # noqa: BLE001
                layer_crs = None
        report = validate_plan(plan, layer_crs=layer_crs)
        self._append(format_validation(report))
        if not report.ok:
            self._append("Le plan comporte des erreurs : exécution annulée.")
            self._reset()
            return

        if requires_confirmation(plan) and not self._confirm(plan):
            self._append("Exécution annulée par l'utilisateur.")
            self._reset()
            return

        self._execute(plan)

    def _confirm(self, plan) -> bool:
        steps = risky_steps(plan)
        lines = "\n".join(f"• {s.tool} : {s.params}" for s in steps)
        answer = QMessageBox.question(
            self,
            "Confirmer les opérations",
            "Les opérations suivantes vont écrire des sorties :\n\n"
            f"{lines}\n\nConfirmer l'exécution ?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        return answer == QMessageBox.Yes

    def _execute(self, plan) -> None:
        orchestrator = getattr(self, 'orchestrator', None)
        if orchestrator is None:
            self._append("Orchestrateur indisponible.")
            self._reset()
            return
        self.status.setText("Exécution…")
        options = getattr(self, 'orchestrator_defaults', None) or {}
        self._worker = _ExecWorker(orchestrator, plan, options=options)
        self._worker.finished_report.connect(self._on_executed)
        self._worker.failed.connect(self._on_failed)
        self._worker.start()

    def _on_executed(self, report, exec_report) -> None:
        self._append(format_execution(exec_report))
        self._append("Terminé." if exec_report.ok else "Terminé avec des erreurs.")
        self._reset()

    def _on_failed(self, message: str) -> None:
        self._append(f"Erreur : {message}")
        self._reset()

    def _reset(self) -> None:
        self.send_button.setEnabled(True)
        self.status.setText("Prêt.")