"""Panneau de dialogue TerangaGIS (S06).

Interface en français : saisie d'instruction, affichage du plan, confirmation
des opérations risquées puis exécution via le bridge. Les appels (LLM, bridge)
tournent dans un thread worker pour ne pas bloquer QGIS (règle R6).
"""
from __future__ import annotations

import threading

from qgis.PyQt.QtCore import QThread, pyqtSignal
from qgis.PyQt.QtWidgets import (QHBoxLayout, QLabel, QMessageBox, QPlainTextEdit,
                                 QPushButton, QVBoxLayout, QWidget)

from plugin.agent.conversation import Conversation
from plugin.agent.policy import requires_confirmation, risky_steps
from plugin.agent.validation import validate_plan
from plugin.ui.formatting import format_execution, format_plan, format_validation


class _PlanWorker(QThread):
    plan_ready = pyqtSignal(object)
    failed = pyqtSignal(str)

    def __init__(self, agent, instruction: str, context: str = '', conversation=None) -> None:
        super().__init__()
        self.agent = agent
        self.instruction = instruction
        self.context = context
        self.conversation = conversation

    def run(self) -> None:  # noqa: D401
        try:
            plan = self.agent.plan(self.instruction, context=self.context, conversation=self.conversation)
        except Exception as e:  # noqa: BLE001
            self.failed.emit(str(e))
            return
        self.plan_ready.emit(plan)


class _ExecWorker(QThread):
    finished_report = pyqtSignal(object, object)
    failed = pyqtSignal(str)
    step_started = pyqtSignal(int, int, str)

    def __init__(self, orchestrator, plan, layer_crs=None, protected_sources=None,
                 options=None, cancel_event=None) -> None:
        super().__init__()
        self.orchestrator = orchestrator
        self.plan = plan
        self.layer_crs = layer_crs
        self.protected_sources = protected_sources
        self.options = dict(options or {})
        self.cancel_event = cancel_event
        self.total = len(getattr(plan, 'steps', []) or [])

    def _on_step_start(self, index, step) -> None:
        self.step_started.emit(int(index), self.total, getattr(step, 'tool', '?'))

    def run(self) -> None:  # noqa: D401
        options = dict(self.options)
        options.setdefault('on_step_start', self._on_step_start)
        if self.cancel_event is not None:
            options.setdefault('should_cancel', self.cancel_event.is_set)
        try:
            report, exec_report = self.orchestrator.run(
                self.plan,
                layer_crs=self.layer_crs,
                protected_sources=self.protected_sources,
                **options,
            )
        except Exception as e:  # noqa: BLE001
            self.failed.emit(str(e))
            return
        self.finished_report.emit(report, exec_report)


class _RepairWorker(QThread):
    """Une seule tentative de correction LLM d'une étape échouée (S13)."""

    repaired = pyqtSignal(object)
    failed = pyqtSignal(str)

    def __init__(self, agent, failed_step, error_message, context='') -> None:
        super().__init__()
        self.agent = agent
        self.failed_step = failed_step
        self.error_message = error_message
        self.context = context

    def run(self) -> None:  # noqa: D401
        try:
            plan = self.agent.repair(self.failed_step, self.error_message, context=self.context)
        except Exception as e:  # noqa: BLE001
            self.failed.emit(str(e))
            return
        self.repaired.emit(plan)


class ChatPanel(QWidget):
    def __init__(self, agent, orchestrator, context_provider=None, parent=None) -> None:
        super().__init__(parent)
        self.agent = agent
        self.orchestrator = orchestrator
        self.context_provider = context_provider
        self.conversation = Conversation()
        self._plan = None
        self._worker = None
        self._instruction = ''
        self._repaired_once = False
        self._cancel_event = threading.Event()
        self.progress_log = []
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

        self.cancel_button = QPushButton("Annuler")
        self.cancel_button.setEnabled(False)
        self.cancel_button.clicked.connect(self.cancel)
        row.addWidget(self.cancel_button)
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
        self.cancel_button.setEnabled(False)
        self._cancel_event.clear()
        self.progress_log = []
        self._repaired_once = False
        self._instruction = instruction
        self._append(f"Vous : {instruction}")
        self.status.setText("Analyse de la demande…")

        context = ''
        provider = getattr(self, 'context_provider', None)
        if callable(provider):
            try:
                context = provider() or ''
            except Exception:  # noqa: BLE001
                context = ''

        self._worker = _PlanWorker(self.agent, instruction, context, self.conversation)
        self._worker.plan_ready.connect(self._on_plan)
        self._worker.failed.connect(self._on_failed)
        self._worker.start()

    def _on_plan(self, plan) -> None:
        self._plan = plan
        self.conversation.add_user(self._instruction)
        if getattr(plan, 'clarification', None):
            self.conversation.add_assistant(plan.clarification)
            self._append(f"Question : {plan.clarification}")
            self._reset()
            self.status.setText("En attente de votre réponse…")
            return
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

        self.conversation.add_plan(plan)
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
        self._cancel_event = threading.Event()
        self.status.setText("Exécution…")
        self.cancel_button.setEnabled(True)
        options = getattr(self, 'orchestrator_defaults', None) or {}
        self._worker = _ExecWorker(
            orchestrator, plan, options=options, cancel_event=self._cancel_event,
        )
        self._worker.step_started.connect(self._on_step_started)
        self._worker.finished_report.connect(self._on_executed)
        self._worker.failed.connect(self._on_failed)
        self._worker.start()

    def _on_step_started(self, index: int, total: int, tool: str) -> None:
        self.progress_log.append((index, total, tool))
        self.status.setText(f"Exécution… étape {index + 1}/{total} : {tool}")

    def cancel(self) -> None:
        """Demande l'annulation de l'exécution en cours (S14)."""
        worker = getattr(self, '_worker', None)
        if worker is None or not worker.isRunning():
            return
        self._cancel_event.set()
        self.cancel_button.setEnabled(False)
        self.status.setText("Annulation demandée…")

    def _on_executed(self, report, exec_report) -> None:
        self._append(format_execution(exec_report))
        self.conversation.add_execution(exec_report)
        if getattr(exec_report, 'cancelled', False):
            self._append("Exécution annulée.")
            self._reset()
            return
        if not exec_report.ok and getattr(exec_report, 'recoverable', False) and not self._repaired_once:
            self._attempt_repair(exec_report)
            return
        self._append("Terminé." if exec_report.ok else "Terminé avec des erreurs.")
        self._reset()

    def _attempt_repair(self, exec_report) -> None:
        failed_step = exec_report.failed_step
        if failed_step is None or self.agent is None:
            self._append("Terminé avec des erreurs.")
            self._reset()
            return
        if not self._confirm_repair(failed_step):
            self._append("Correction refusée.")
            self._reset()
            return
        self._repaired_once = True
        self.status.setText("Correction de l'étape échouée (1 essai)…")
        error = (failed_step.result or {}).get('error') or {}
        self._worker = _RepairWorker(
            self.agent, failed_step, error.get('message', ''), context=self._repair_context(),
        )
        self._worker.repaired.connect(self._on_repaired)
        self._worker.failed.connect(self._on_failed)
        self._worker.start()

    def _on_repaired(self, plan) -> None:
        if not getattr(plan, 'steps', None):
            self._append("Aucune correction proposée.")
            self._reset()
            return
        self._append("Correction proposée :")
        self._append(format_plan(plan))
        self._execute(plan)

    def _repair_context(self) -> str:
        provider = getattr(self, 'context_provider', None)
        if callable(provider):
            try:
                return provider() or ''
            except Exception:  # noqa: BLE001
                return ''
        return ''

    def _confirm_repair(self, failed_step) -> bool:
        answer = QMessageBox.question(
            self,
            "Corriger automatiquement",
            f"L'étape « {failed_step.tool} » a échoué.\n\n"
            "Demander à l'agent une correction (une seule tentative) ?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.Yes,
        )
        return answer == QMessageBox.Yes

    def _on_failed(self, message: str) -> None:
        self._append(f"Erreur : {message}")
        self._reset()

    def _reset(self) -> None:
        self.send_button.setEnabled(True)
        self.cancel_button.setEnabled(False)
        self.status.setText("Prêt.")