"""Classification d'erreurs et calcul de backoff (S12 — V2 Workflow Agent).

Module **pur** (aucune dépendance QGIS), partagé par l'orchestrateur (retries
d'étape) et le client LLM. On distingue :

- les erreurs **transitoires** (`transient`) : à réessayer (réseau, quota, 5xx,
  exception d'outil ponctuelle) ;
- les erreurs **permanentes** (`permanent`) : réessayer ne sert à rien (paramètre
  manquant, couche introuvable, outil inconnu, sortie invalide) ;
- les erreurs **inconnues** (`unknown`) : non réessayées par défaut, mais
  signalées comme récupérables (une reprise contrôlée reste possible, S13).
"""
from __future__ import annotations

import random
from typing import Any, Dict, Optional

TRANSIENT = 'transient'
PERMANENT = 'permanent'
UNKNOWN = 'unknown'

TRANSIENT_CODES = frozenset({
    'internal',
    'tool_exception',
    'client_error',
    'timeout',
    'connection_error',
    'rate_limited',
    'server_error',
    'service_unavailable',
    'quota_exceeded',
    'llm_transport',
})

PERMANENT_CODES = frozenset({
    'missing_param',
    'invalid_param',
    'bad_distance',
    'invalid_distance',
    'layer_not_found',
    'unknown_tool',
    'tool_not_found',
    'unsupported',
    'output_overwrites_source',
    'write_error',
    'no_iface',
    'unauthorized',
    'bad_request',
    'not_found',
})


def classify_error(error: Any) -> str:
    """Classe une erreur (`{'code': ...}`, `code` ou `None`) en transient/permanent/unknown."""
    if not error:
        return UNKNOWN
    if isinstance(error, str):
        code = error
    elif isinstance(error, dict):
        code = str(error.get('code') or '')
    else:
        code = str(getattr(error, 'code', '') or '')
    if code in TRANSIENT_CODES:
        return TRANSIENT
    if code in PERMANENT_CODES:
        return PERMANENT
    return UNKNOWN


def is_retryable(error: Any) -> bool:
    """Vrai si l'erreur mérite une nouvelle tentative automatique."""
    return classify_error(error) == TRANSIENT


def backoff_seconds(attempt: int, base: float = 0.5, cap: float = 8.0, jitter: float = 0.0) -> float:
    """Délai d'attente exponentiel pour la tentative `attempt` (1-indexée)."""
    if attempt < 1:
        attempt = 1
    delay = min(cap, max(0.0, float(base)) * (2 ** (attempt - 1)))
    if jitter:
        delay += random.uniform(0.0, jitter)
    return delay
