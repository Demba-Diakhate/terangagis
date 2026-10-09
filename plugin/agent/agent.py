"""Agent IA : planification d'appels d'outils à partir d'une instruction.

S04 : planification uniquement (aucune exécution — voir S05).
S15 : l'agent peut demander une clarification au lieu de deviner
(`AgentPlan.clarification`), via le pseudo-outil `request_clarification`.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from .llm import LLMClient, LLMError
from .prompts import SYSTEM_PROMPT
from .sanitization import sanitize_text
from .tools_schema import CLARIFICATION_TOOL_NAME, TOOL_NAMES, openai_tools


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
    clarification: Optional[str] = None


class AgentError(Exception):
    pass


class GeoAgent:
    def __init__(self, llm: LLMClient | None = None, journal: Any = None, parse_retries: int = 1) -> None:
        self.llm = llm or LLMClient()
        self.journal = journal
        self.parse_retries = max(0, int(parse_retries))

    def plan(self, user_query: str, context: str = '', conversation: Any = None) -> AgentPlan:
        """Produit un plan (liste d'étapes) sans exécuter les outils.

        Si `conversation` est fourni (objet avec une méthode `messages()`), son
        historique est injecté avant la demande courante (S13). Si la réponse du
        LLM n'est pas exploitable (JSON d'arguments invalide, outil inconnu),
        l'agent redemande une correction, au plus `parse_retries` fois (règle R3).

        Le LLM peut aussi demander une clarification (S15) : le plan retourné a
        alors `clarification` renseigné et aucune étape.
        """
        if not user_query or not user_query.strip():
            raise AgentError('Instruction vide.')

        user_query = sanitize_text(user_query, max_length=2000)
        context = sanitize_text(context, max_length=4000) if context else ''

        base_messages: List[Dict[str, Any]] = [{'role': 'system', 'content': SYSTEM_PROMPT}]
        if context:
            base_messages.append({'role': 'system', 'content': f'Contexte QGIS :\n{context}'})
        history = self._conversation_messages(conversation)
        if history:
            base_messages.extend(history)
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
                message = self.llm.chat(messages, tools=openai_tools(include_clarification=True))
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
    def _conversation_messages(conversation: Any) -> List[Dict[str, str]]:
        if conversation is None:
            return []
        try:
            history = conversation.messages()
        except Exception:  # noqa: BLE001
            return []
        return list(history or [])[:2 * getattr(conversation, 'max_turns', 12)]

    def repair(self, failed_step: Any, error_message: str, context: str = '') -> AgentPlan:
        """Demande au LLM une correction pour une étape échouée (S13).

        Retourne un plan de remplacement (les étapes à exécuter à la place).
        Un seul essai : l'appelant décide de relancer ou d'abandonner.
        """
        tool = getattr(failed_step, 'tool', '?')
        params = getattr(failed_step, 'params', {}) or {}
        context = sanitize_text(context, max_length=4000) if context else ''
        error_message = sanitize_text(str(error_message), max_length=500)

        messages: List[Dict[str, Any]] = [{'role': 'system', 'content': SYSTEM_PROMPT}]
        if context:
            base = f'Contexte QGIS :\n{context}'
            messages.append({'role': 'system', 'content': base})
        messages.append({
            'role': 'user',
            'content': (
                f"L'étape « {tool} » avec les paramètres {params} a échoué : {error_message}. "
                "Propose une correction en un ou plusieurs appels d'outils valides qui "
                "remplacent cette étape. N'inclus que les étapes à exécuter, sans explication."
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
            if name == CLARIFICATION_TOOL_NAME:
                question = GeoAgent._clarification_question(function.get('arguments'))
                return AgentPlan(clarification=question, assistant_text=message.get('content') or '')
            if not name or name not in TOOL_NAMES:
                raise AgentError(f"Appel d'outil invalide : {name!r}")
            raw_args = function.get('arguments') or '{}'
            try:
                params = json.loads(raw_args) if isinstance(raw_args, str) else dict(raw_args)
            except json.JSONDecodeError as e:
                raise AgentError(f"Arguments JSON invalides pour {name}: {e}") from e
            steps.append(AgentStep(tool=name, params=params))
        return AgentPlan(steps=steps, assistant_text=message.get('content') or '')

    @staticmethod
    def _clarification_question(raw_arguments: Any) -> str:
        """Extrait et nettoie la question d'un appel `request_clarification`."""
        if isinstance(raw_arguments, str):
            try:
                arguments = json.loads(raw_arguments) if raw_arguments else {}
            except json.JSONDecodeError as e:
                raise AgentError(f'Arguments de clarification invalides : {e}') from e
        elif isinstance(raw_arguments, dict):
            arguments = raw_arguments
        else:
            arguments = {}
        question = str(arguments.get('question', '') or '').strip()
        if not question:
            raise AgentError('Clarification demandée sans question.')
        return sanitize_text(question, max_length=500).strip()
