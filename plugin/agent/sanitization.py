"""Sanitisation des données envoyées au LLM (RT7).

Objectif : ne jamais transmettre de valeurs attributaires brutes, longues ou
sensibles. On tronque, on échappe les caractères de contrôle et on neutralise
les motifs qui ressemblent à des secrets.
"""
from __future__ import annotations

import re
from typing import Any, Dict, Iterable, List

MAX_STRING_LENGTH = 200
MAX_ITEMS = 50

_SECRET_PATTERNS = [
    re.compile(r'sk-[A-Za-z0-9]{8,}'),
    re.compile(r'Bearer\s+[A-Za-z0-9._\-]+', re.IGNORECASE),
    re.compile(r'(api[_-]?key|token|secret|password)\s*[:=]\s*\S+', re.IGNORECASE),
]

_CONTROL_CHARS = re.compile(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]')


def sanitize_text(value: str, max_length: int = MAX_STRING_LENGTH) -> str:
    text = _CONTROL_CHARS.sub('', str(value))
    for pattern in _SECRET_PATTERNS:
        text = pattern.sub('[secret]', text)
    if len(text) > max_length:
        text = text[:max_length] + '…'
    return text


def sanitize_value(value: Any, max_length: int = MAX_STRING_LENGTH) -> Any:
    if isinstance(value, str):
        return sanitize_text(value, max_length)
    if isinstance(value, dict):
        return sanitize_mapping(value, max_length)
    if isinstance(value, (list, tuple)):
        return [sanitize_value(v, max_length) for v in list(value)[:MAX_ITEMS]]
    if isinstance(value, (int, float, bool)) or value is None:
        return value
    return sanitize_text(str(value), max_length)


def sanitize_mapping(data: Dict[str, Any], max_length: int = MAX_STRING_LENGTH) -> Dict[str, Any]:
    out: Dict[str, Any] = {}
    for key, value in list(data.items())[:MAX_ITEMS]:
        out[sanitize_text(str(key))] = sanitize_value(value, max_length)
    return out


def sanitize_lines(lines: Iterable[str], max_length: int = MAX_STRING_LENGTH) -> List[str]:
    return [sanitize_text(line, max_length) for line in lines]