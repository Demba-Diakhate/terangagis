"""Abstraction LLM compatible OpenAI (OpenRouter / Gemini).

Aucune dépendance externe : utilise `urllib` (compatible Python embarqué QGIS).
Le `transport` est injectable pour les tests (aucune clé requise).
"""
from __future__ import annotations

import json
from typing import Any, Callable, Dict, List

from common.config import Settings, load_settings

Message = Dict[str, Any]
Transport = Callable[[str, Dict[str, str], bytes, float], Dict[str, Any]]


class LLMError(Exception):
    """Erreur d'appel au LLM."""


def _urllib_transport(url: str, headers: Dict[str, str], body: bytes, timeout: float) -> Dict[str, Any]:
    from urllib import request as _request
    from urllib.error import HTTPError, URLError

    req = _request.Request(url, data=body, headers=headers, method='POST')
    try:
        with _request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode('utf-8'))
    except HTTPError as e:  # noqa: PERF203
        detail = e.read().decode('utf-8', errors='replace')
        raise LLMError(f'HTTP {e.code} du fournisseur LLM : {detail}') from e
    except URLError as e:
        raise LLMError(f'Connexion au fournisseur LLM impossible : {e}') from e


class LLMClient:
    def __init__(self, settings: Settings | None = None, transport: Transport | None = None) -> None:
        self.settings = settings or load_settings()
        self._transport = transport or _urllib_transport

    @property
    def ready(self) -> bool:
        return self.settings.is_ready

    def chat(
        self,
        messages: List[Message],
        tools: List[Dict[str, Any]] | None = None,
        tool_choice: str = 'auto',
        temperature: float = 0.0,
    ) -> Message:
        if not self.ready:
            raise LLMError(
                "Aucune clé API configurée. Renseigne OPENROUTER_API_KEY ou GEMINI_API_KEY."
            )
        payload: Dict[str, Any] = {
            'model': self.settings.model,
            'messages': messages,
            'temperature': temperature,
        }
        if tools:
            payload['tools'] = tools
            payload['tool_choice'] = tool_choice

        url = f'{self.settings.base_url}/chat/completions'
        headers = {
            'Authorization': f'Bearer {self.settings.api_key}',
            'Content-Type': 'application/json',
        }
        body = json.dumps(payload).encode('utf-8')

        last_error: Exception | None = None
        for _ in range(max(1, self.settings.max_retries + 1)):
            try:
                data = self._transport(url, headers, body, float(self.settings.timeout))
                return self._extract_message(data)
            except LLMError as e:
                last_error = e
        raise LLMError(str(last_error) if last_error else 'Échec LLM inconnu')

    @staticmethod
    def _extract_message(data: Dict[str, Any]) -> Message:
        try:
            return data['choices'][0]['message']
        except (KeyError, IndexError, TypeError) as e:
            raise LLMError(f'Réponse LLM inattendue : {data!r}') from e