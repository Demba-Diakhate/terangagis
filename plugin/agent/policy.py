"""Politique de confirmation des opérations (sécurité).

Les outils en lecture seule (inspection, sélection) n'exigent pas de
confirmation ; les opérations qui écrivent des sorties ou modifient des données
doivent être confirmées par l'utilisateur avant exécution.
"""
from __future__ import annotations

from typing import Any, List

READ_ONLY_TOOLS = {
    'get_project_info',
    'list_layers',
    'get_layer_info',
    'get_selected_features',
    'select_by_attribute',
}


def risky_steps(plan: Any) -> List[Any]:
    """Retourne les étapes nécessitant une confirmation."""
    return [s for s in getattr(plan, 'steps', []) if s.tool not in READ_ONLY_TOOLS]


def requires_confirmation(plan: Any) -> bool:
    return bool(risky_steps(plan))