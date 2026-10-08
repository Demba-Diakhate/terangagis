"""Corpus golden et évaluation de l'agent (RT2).

Sans dépendance QGIS : charge un corpus d'instructions FR avec les appels
d'outils attendus, valide sa structure et note un plan produit par l'agent.
L'évaluation réelle (avec LLM) s'exécute hors CI via `scripts/run_golden.py`.
"""
from __future__ import annotations

import json
from typing import Any, Dict, List, Sequence


def load_corpus(path: str) -> List[Dict[str, Any]]:
    with open(path, 'r', encoding='utf-8') as fh:
        data = json.load(fh)
    if isinstance(data, dict):
        return list(data.get('cases', []))
    return list(data)


def validate_corpus(cases: Sequence[Dict[str, Any]], known_tools: Sequence[str]) -> List[str]:
    known = set(known_tools)
    errors: List[str] = []
    seen = set()
    for i, case in enumerate(cases):
        cid = case.get('id')
        label = cid or f'#{i}'
        if not cid:
            errors.append(f"case {label}: 'id' manquant")
        elif cid in seen:
            errors.append(f"case {label}: 'id' dupliqué")
        else:
            seen.add(cid)
        instruction = case.get('instruction')
        if not instruction or not str(instruction).strip():
            errors.append(f"case {label}: 'instruction' manquante")
        expected = case.get('expected_tools')
        if not expected:
            errors.append(f"case {label}: 'expected_tools' vide")
        else:
            for tool in expected:
                if tool not in known:
                    errors.append(f"case {label}: outil inconnu '{tool}'")
    return errors


def score_plan(expected: Sequence[str], actual: Sequence[str]) -> Dict[str, Any]:
    """Compare les outils attendus et produits (ensembles + ordre exact)."""
    exp = list(expected)
    act = list(actual)
    exp_set, act_set = set(exp), set(act)
    tp = exp_set & act_set
    precision = len(tp) / len(act_set) if act_set else 0.0
    recall = len(tp) / len(exp_set) if exp_set else 1.0
    return {
        'exact': exp == act,
        'expected': exp,
        'actual': act,
        'missing': [t for t in exp if t not in act_set],
        'extra': [t for t in act if t not in exp_set],
        'precision': precision,
        'recall': recall,
    }


def evaluate(cases: Sequence[Dict[str, Any]], plan_fn) -> Dict[str, Any]:
    """Évalue un corpus. `plan_fn(instruction, context) -> list[str]` (outils du plan)."""
    results = []
    passed = 0
    for case in cases:
        try:
            actual = plan_fn(case['instruction'], case.get('context', ''))
        except Exception as e:  # noqa: BLE001
            actual = list(case.get('actual_tools', []))
            results.append({'id': case.get('id'), 'ok': False, 'error': str(e)})
            continue
        score = score_plan(case['expected_tools'], actual)
        ok = score['recall'] == 1.0 and score['precision'] == 1.0
        if ok:
            passed += 1
        results.append({'id': case.get('id'), 'ok': ok, **score})
    total = len(cases)
    return {
        'total': total,
        'passed': passed,
        'score': (passed / total) if total else 0.0,
        'results': results,
    }