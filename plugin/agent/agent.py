"""Agent IA : planification d'appels d'outils à partir d'une instruction.

S04 : planification uniquement (aucune exécution — voir S05).
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any, Dict, List

from .llm import LLMClient, LLMError
from .prompts import SYSTEM_PROMPT
from .sanitization import sanitize_text
from .tools_schema import TOOL_NAMES, openai_tools


@dataclass
class AgentStep:
    tool: str
    params: Dict[str, Any] = field(default_factory=dict)
    on_error: str | None = None
    max_retries: int | None = None


@dataclass
class AgentPlan:
    steps: List[AgentStep] = field(default_factory=list)
    assistant_text: str = ''


class AgentError(Exception):
    pass


class GeoAgent:
    def __init__(self, llm: LLMClient | None = None, journal: Any = None, parse_retries: int = 1) -> None:
        self.llm = llm or LLMClient()
        self.journal = journal
        self.parse_retries = max(0, int(parse_retries))

    def plan(self, user_query: str, context: str = '') -> AgentPlan:
        """Produit un plan (liste d'étapes) sans exécuter les outils.

        Si la réponse du LLM n'est pas exploitable (JSON d'arguments invalide,
        outil inconnu), l'agent redemande une correction, au plus `parse_retries`
        fois (règle R3).
        """
        if not user_query or not user_query.strip():
            raise AgentError('Instruction vide.')

        user_query = sanitize_text(user_query, max_length=2000)
        context = sanitize_text(context, max_length=4000) if context else ''

        base_messages: List[Dict[str, Any]] = [{'role': 'system', 'content': SYSTEM_PROMPT}]
        if context:
            base_messages.append({'role': 'system', 'content': f'Contexte QGIS :\n{context}'})
        base_messages.append({'role': 'user', 'content': user_query})

        attempts = 1 + self.parse_retries
        last_error: AgentError | None = None
        for attempt in range(attempts):
            messages = list(base_messages)
            if attempt > 0 and last_error is not None:
                messages.append({
                    'role': 'user',
                    'content': (
                        f"Ta réponse précédente était invalide : {last_error}. "
                        "Réessaie en utilisant uniquement les outils disponibles et des "
                        "arguments JSON valides."
                    ),
                })
            try:
                message = self.llm.chat(messages, tools=openai_tools())
            except LLMError as e:
                raise AgentError(str(e)) from e

            if self.journal is not None:
                try:
                    self.journal.record_llm(messages, message)
                except Exception:  # noqa: BLE001
                    pass

            try:
                plan = self._parse(message)
            except AgentError as e:
                last_error = e
                continue

            if self.journal is not None:
                try:
                    self.journal.record_plan(plan)
                except Exception:  # noqa: BLE001
                    pass
            return plan

        raise last_error or AgentError('Plan invalide.')

    @staticmethod
    def _parse(message: Dict[str, Any]) -> AgentPlan:
        steps: List[AgentStep] = []
        for call in message.get('tool_calls') or []:
            function = call.get('function') or {}
            name = function.get('name')
            if not name or name not in TOOL_NAMES:
                raise AgentError(f"Appel d'outil invalide : {name!r}")
            raw_args = function.get('arguments') or '{}'
            try:
                params = json.loads(raw_args) if isinstance(raw_args, str) else dict(raw_args)
            except json.JSONDecodeError as e:
                raise AgentError(f"Arguments JSON invalides pour {name}: {e}") from e
            steps.append(AgentStep(tool=name, params=params))
        return AgentPlan(steps=steps, assistant_text=message.get('content') or '')