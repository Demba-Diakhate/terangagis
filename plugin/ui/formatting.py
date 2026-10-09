"""Mise en forme (français) des plans, validations et résultats.

Module sans dépendance Qt/QGIS : testable en pur Python.
"""
from __future__ import annotations

from typing import Any, Dict, List


def format_plan(plan: Any) -> str:
    steps = getattr(plan, 'steps', []) or []
    if not steps:
        return "Aucune étape."
    lines = []
    for i, step in enumerate(plan.steps, 1):
        params = ', '.join(f'{k}={v!r}' for k, v in (step.params or {}).items())
        lines.append(f"{i}. {step.tool}({params})")
    text = '\n'.join(lines)
    assistant = getattr(plan, 'assistant_text', '')
    if assistant:
        return f"{assistant}\n\nPlan :\n{text}"
    return f"Plan :\n{text}"


def format_validation(report: Any) -> str:
    issues = getattr(report, 'issues', [])
    if not issues:
        return "Validation : OK."
    lines = []
    for issue in issues:
        prefix = 'ERREUR' if issue.level == 'error' else 'Attention'
        lines.append(f"[{prefix}] {issue.message}")
    return "Validation :\n" + "\n".join(lines)


def format_execution(report: Any) -> str:
    steps = getattr(report, 'steps', [])
    if not steps:
        return "Aucune étape exécutée."
    lines = []
    for i, step in enumerate(steps, 1):
        if step.ok:
            data = step.result.get('data') if step.result else None
            detail = f" — {data}" if data else ''
            lines.append(f"{i}. {step.tool} : OK{detail}")
        else:
            error = (step.result or {}).get('error') or {}
            lines.append(f"{i}. {step.tool} : ÉCHEC — {error.get('message', 'inconnu')}")
    if getattr(report, 'cancelled', False):
        lines.append("(exécution annulée par l'utilisateur)")
    elif getattr(report, 'stopped_on_error', False):
        lines.append("(exécution interrompue après une erreur)")
    return "Résultats :\n" + "\n".join(lines) if lines else "Résultats :\n(aucune étape exécutée)"