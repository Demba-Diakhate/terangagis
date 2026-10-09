"""Abstraction LLM compatible OpenAI (OpenRouter / Gemini).

Aucune dépendance externe : utilise `urllib` (compatible Python embarqué QGIS).
Le `transport` est injectable pour les tests (aucune clé requise).

Durci en S12 : les erreurs sont classées réessables ou non (4xx définitif,
429/5xx/timeout réessable), le backoff est exponentiel et `Retry-After` est
respecté si le fournisseur le fournit.
"""
from __future__ import annotations

import json
import time
from typing import Any, Callable, Dict, List

from common.config import Settings, load_settings

from .retry import backoff_seconds

Message = Dict[str, Any]
Transport = Callable[[str, Dict[str, str], bytes, float], Dict[str, Any]]


class LLMError(Exception):
    """Erreur d'appel au LLM (avec indication de réessai)."""

    def __init__(self, message: str, *, retryable: bool = True, retry_after: float | None = None) -> None:
        super().__init__(message)
        self.retryable = retryable
        self.retry_after = retry_after


def _retry_after_from_headers(headers: Any) -> float | None:
    try:
        raw = headers.get('Retry-After') if headers is not None else None
        return float(raw) if raw else None
    except (TypeError, ValueError):
        return None


def _urllib_transport(url: str, headers: Dict[str, str], body: bytes, timeout: float) -> Dict[str, Any]:
    from urllib import request as _request
    from urllib.error import HTTPError, URLError

    req = _request.Request(url, data=body, headers=headers, method='POST')
    try:
        with _request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode('utf-8'))
    except HTTPError as e:
        detail = e.read().decode('utf-8', errors='replace')
        retryable = e.code in (408, 409, 425, 429) or e.code >= 500
        raise LLMError(
            f'HTTP {e.code} du fournisseur LLM : {detail}',
            retryable=retryable,
            retry_after=_retry_after_from_headers(getattr(e, 'headers', None)),
        ) from e
    except URLError as e:
        raise LLMError(f'Connexion au fournisseur LLM impossible : {e}', retryable=True) from e


class LLMClient:
    def __init__(
        self,
        settings: Settings | None = None,
        transport: Transport | None = None,
        sleep: Callable[[float], None] | None = None,
    ) -> None:
        self.settings = settings or load_settings()
        self._transport = transport or _urllib_transport
        self._sleep = sleep or time.sleep

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

        max_retries = max(0, int(self.settings.max_retries))
        last_error: Exception | None = None
        for attempt in range(max_retries + 1):
            try:
                data = self._transport(url, headers, body, float(self.settings.timeout))
                return self._extract_message(data)
            except LLMError as e:
                last_error = e
                if not e.retryable or attempt >= max_retries:
                    raise
                delay = e.retry_after if e.retry_after is not None else backoff_seconds(
                    attempt + 1, self.settings.llm_backoff,
                )
                self._sleep(delay)
        raise LLMError(str(last_error) if last_error else 'Échec LLM inconnu')

    @staticmethod
    def _extract_message(data: Dict[str, Any]) -> Message:
        try:
            return data['choices'][0]['message']
        except (KeyError, IndexError, TypeError) as e:
            raise LLMError(f'Réponse LLM inattendue : {data!r}', retryable=False) from e
