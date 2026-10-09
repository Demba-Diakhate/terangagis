"""Schémas d'outils pour le tool calling (format OpenAI).

Réutilise les définitions de `mcp.server.TOOL_SCHEMAS` (sans dépendance QGIS).

S15 ajoute un pseudo-outil `request_clarification` **optionnel** : il permet à
l'agent de poser une question de clarification au lieu de deviner. Il n'est pas
exposé par le serveur MCP (il est absent de `TOOL_NAMES`).
"""
from __future__ import annotations

from typing import Any, Dict, List

from mcp.server import TOOL_SCHEMAS

CLARIFICATION_TOOL_NAME = "request_clarification"

__all__ = ["TOOL_SCHEMAS", "TOOL_NAMES", "CLARIFICATION_TOOL_NAME",
           "openai_tools", "clarification_tool"]


def clarification_tool() -> Dict[str, Any]:
    """Décrit le pseudo-outil de clarification (S15), au format OpenAI."""
    return {
        "type": "function",
        "function": {
            "name": CLARIFICATION_TOOL_NAME,
            "description": (
                "Pose une question de clarification à l'utilisateur lorsque la "
                "demande est ambiguë ou incomplète (couche, paramètre, unité ou "
                "sortie manquante). Ne l'utilise que si l'information ne peut pas "
                "être raisonnablement déduite ; une seule question à la fois."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "question": {
                        "type": "string",
                        "description": "La question de clarification, en français.",
                    },
                },
                "required": ["question"],
            },
        },
    }


def openai_tools(include_clarification: bool = False) -> List[Dict[str, Any]]:
    tools: List[Dict[str, Any]] = []
    for name, spec in TOOL_SCHEMAS.items():
        tools.append({
            "type": "function",
            "function": {
                "name": name,
                "description": spec.get("description", ""),
                "parameters": {
                    "type": "object",
                    "properties": spec.get("properties", {}),
                    "required": spec.get("required", []),
                },
            },
        })
    if include_clarification:
        tools.append(clarification_tool())
    return tools


TOOL_NAMES = set(TOOL_SCHEMAS.keys())
