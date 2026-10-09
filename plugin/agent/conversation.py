"""Mémoire de conversation en mémoire (S13, V2 Workflow Agent).

Conserve, pour la durée de la session du panneau QGIS, l'historique des
échanges (instruction → plan → exécution) afin que l'agent tienne compte du
contexte précédent (reformulations, « reprends », sorties déjà produites).

Module **pur** (aucune dépendance QGIS) et plafonné en taille (budget en
caractères et en tours) pour ne pas faire exploser le prompt (RT7).
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List

from .sanitization import sanitize_text

DEFAULT_MAX_CHARS = 6000
DEFAULT_MAX_TURNS = 12


@dataclass
class Turn:
    role: str
    content: str


class Conversation:
    """Historique d'échanges en mémoire, borné."""

    def __init__(self, max_chars: int = DEFAULT_MAX_CHARS, max_turns: int = DEFAULT_MAX_TURNS) -> None:
        self.max_chars = max(200, int(max_chars))
        self.max_turns = max(1, int(max_turns))
        self._turns: List[Turn] = []
        self.artifacts: List[str] = []

    def add_user(self, text: str) -> None:
        self._append('user', text)

    def add_assistant(self, text: str) -> None:
        self._append('assistant', text)

    def add_plan(self, plan: Any) -> None:
        """Ajoute un résumé du plan proposé comme tour assistant."""
        steps = getattr(plan, 'steps', None) or []
        tools = [getattr(step, 'tool', '?') for step in steps]
        summary = 'Plan proposé : ' + (' → '.join(tools) if tools else 'aucune étape')
        text = getattr(plan, 'assistant_text', '') or ''
        if text:
            summary = f'{text} | {summary}'
        self.add_assistant(summary)

    def add_execution(self, exec_report: Any) -> None:
        steps = getattr(exec_report, 'steps', None) or []
        produced = self._collect_artifacts(steps)
        if getattr(exec_report, 'cancelled', False):
            parts = [f"Exécution annulée par l'utilisateur ({len(steps)} étape(s) exécutée(s))"]
        elif getattr(exec_report, 'ok', False):
            parts = [f'Exécution réussie ({len(steps)} étape(s))']
        else:
            failed = getattr(exec_report, 'failed_step', None)
            tool = getattr(failed, 'tool', '?') if failed is not None else '?'
            parts = [f"Exécution en échec à l'étape « {tool} »"]
        if produced:
            parts.append('Sorties : ' + ', '.join(produced))
        self.add_assistant(' | '.join(parts))

    def _collect_artifacts(self, steps: Any) -> List[str]:
        names: List[str] = []
        for step in steps or []:
            result = getattr(step, 'result', None)
            data = result.get('data') if isinstance(result, dict) else None
            if not isinstance(data, dict):
                continue
            name = data.get('artifact')
            if isinstance(name, str) and name and name not in names:
                names.append(name)
                if name not in self.artifacts:
                    self.artifacts.append(name)
        return names

    def messages(self) -> List[Dict[str, str]]:
        """Retourne les tours récents (du plus ancien au plus récent) sous budget."""
        kept: List[Turn] = []
        total = 0
        for turn in reversed(self._turns):
            total += len(turn.content)
            if kept and (total > self.max_chars or len(kept) >= self.max_turns):
                break
            kept.append(turn)
        kept.reverse()
        return [{'role': turn.role, 'content': turn.content} for turn in kept]

    def clear(self) -> None:
        self._turns.clear()
        self.artifacts.clear()

    def __len__(self) -> int:
        return len(self._turns)

    def _append(self, role: str, text: str) -> None:
        content = sanitize_text(str(text), max_length=1000).strip()
        if not content:
            return
        self._turns.append(Turn(role, content))
        overflow = len(self._turns) - self.max_turns
        if overflow > 0:
            del self._turns[0:overflow]
