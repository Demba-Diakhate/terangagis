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


@dataclass
class AgentPlan:
    steps: List[AgentStep] = field(default_factory=list)
    assistant_text: str = ''


class AgentError(Exception):
    pass


class GeoAgent:
    def __init__(self, llm: LLMClient | None = None, journal: Any = None) -> None:
        self.llm = llm or LLMClient()
        self.journal = journal

    def plan(self, user_query: str, context: str = '') -> AgentPlan:
        """Produit un plan (liste d'étapes) sans exécuter les outils."""
        if not user_query or not user_query.strip():
            raise AgentError('Instruction vide.')

        user_query = sanitize_text(user_query, max_length=2000)
        context = sanitize_text(context, max_length=4000) if context else ''

        messages: List[Dict[str, Any]] = [{'role': 'system', 'content': SYSTEM_PROMPT}]
        if context:
            messages.append({'role': 'system', 'content': f'Contexte QGIS :\n{context}'})
        messages.append({'role': 'user', 'content': user_query})

        try:
            message = self.llm.chat(messages, tools=openai_tools())
        except LLMError as e:
            raise AgentError(str(e)) from e

        if self.journal is not None:
            try:
                self.journal.record_llm(messages, message)
            except Exception:  # noqa: BLE001
                pass

        plan = self._parse(message)
        if self.journal is not None:
            try:
                self.journal.record_plan(plan)
            except Exception:  # noqa: BLE001
                pass
        return plan

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