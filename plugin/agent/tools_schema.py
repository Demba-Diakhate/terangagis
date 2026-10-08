"""Schémas d'outils pour le tool calling (format OpenAI).

Réutilise les définitions de `mcp.server.TOOL_SCHEMAS` (sans dépendance QGIS).
"""
from __future__ import annotations

from typing import Any, Dict, List

from mcp.server import TOOL_SCHEMAS


def openai_tools() -> List[Dict[str, Any]]:
    tools: List[Dict[str, Any]] = []
    for name, spec in TOOL_SCHEMAS.items():
        tools.append({
            'type': 'function',
            'function': {
                'name': name,
                'description': spec.get('description', ''),
                'parameters': {
                    'type': 'object',
                    'properties': spec.get('properties', {}),
                    'required': spec.get('required', []),
                },
            },
        })
    return tools


TOOL_NAMES = set(TOOL_SCHEMAS.keys())