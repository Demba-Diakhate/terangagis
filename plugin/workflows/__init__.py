"""Workflows métier TerangaGIS (S08 + Sénégal S25).

Cinq scénarios de démonstration, exprimés comme des plans d'outils
(`AgentPlan`) reproductibles, exécutables sur des jeux de données de test :

1. Accessibilité aux routes (tampon + découpage)  → `road_accessibility`
2. Nettoyage de données GPS (correction + doublons + export) → `gps_cleanup`
3. Accessibilité aux postes de santé (distances euclidiennes) → `health_accessibility`
4. Analyse route/commune Sénégal (distances + sélection) → `sen_route_commune`
5. Proximité hydrographie Sénégal (tampon + découpage) → `sen_hydro_proximite`
"""
from .definitions import (
    WORKFLOWS,
    Workflow,
    build_plan,
    get_workflow,
    list_workflows,
)
from .runner import WorkflowReport, execute_workflow

__all__ = [
    'WORKFLOWS',
    'Workflow',
    'WorkflowReport',
    'build_plan',
    'execute_workflow',
    'get_workflow',
    'list_workflows',
]