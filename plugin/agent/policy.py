"""Politique de confirmation des opérations (sécurité, CDC §16 F07).

Niveaux :
- faible : lecture/inspection → pas de confirmation
- moyen/élevé/critique : opérations qui écrivent/modifient/suppriment → confirmation
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

# Outils nécessitant confirmation obligatoire (modif/suppression potentielle)
CRITICAL_TOOLS = {
    'save_layer',  # peut écraser selon chemin/usage
}

# Opérations qui créent généralement des sorties (buffer/clip/intersection/dissolve/spatial_join/distance_analysis/export_map/fix_geometries/remove_duplicates/reproject_layer)
WRITE_TOOLS = {
    'buffer',
    'clip',
    'intersection',
    'dissolve',
    'spatial_join',
    'distance_analysis',
    'export_map',
    'save_layer',
    'fix_geometries',
    'remove_duplicates',
    'reproject_layer',
}


def _is_risky_tool(tool: str) -> bool:
    if tool in READ_ONLY_TOOLS:
        return False
    if tool in WRITE_TOOLS or tool in CRITICAL_TOOLS:
        return True
    return True  # prudence par défaut


def risky_steps(plan: Any) -> List[Any]:
    """Retourne les étapes nécessitant une confirmation."""
    steps = []
    for s in getattr(plan, 'steps', []):
        tool = getattr(s, 'tool', '')
        if _is_risky_tool(tool):
            steps.append(s)
    return steps


def requires_confirmation(plan: Any) -> bool:
    return bool(risky_steps(plan))
