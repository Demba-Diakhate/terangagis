"""Builders des workflows métier Sénégal (S25 — intégration du socle V5).

Convertis les gabarits déclaratifs de `plugin/senegal_workflows.py` en plans
d'outils exécutables, en réutilisant uniquement les outils existants
(Processing-first, RT1 ; distances euclidiennes, RT5). Les `Workflow`
associés sont enregistrés dans `plugin/workflows/definitions.py`.

Rôles d'entrée :
- `sen_route_commune` : `routes` (lignes) + `communes` (polygones) — le mapping
  retenu est tampon euclidien 5 km + découpage (accessibilité), car
  `distance_analysis` (qgis:distancematrix) n'accepte que des points.
- `sen_hydro_proximite` : `hydro` (lignes) + `zones` (polygones d'étude).
"""
from __future__ import annotations

import os
from typing import Dict

from ..agent.agent import AgentPlan, AgentStep

SEN_ROUTE_DISTANCE_THRESHOLD = 5000   # m — proximité d'une route
SEN_HYDRO_BUFFER_DISTANCE = 2000      # m — proximité d'un cours d'eau


def _layer_name(path: str) -> str:
    """Miroir de `definitions.layer_name_from_path` (évite un import circulaire)."""
    return os.path.splitext(os.path.basename(path))[0]


def build_sen_route_commune(layers: Dict[str, str], out_dir: str) -> AgentPlan:
    buffer_path = os.path.join(out_dir, 'routes_buffer_sen.gpkg')
    result_path = os.path.join(out_dir, 'communes_acces_routes.gpkg')
    return AgentPlan(
        steps=[
            AgentStep('buffer', {
                'layer': layers['routes'],
                'distance': SEN_ROUTE_DISTANCE_THRESHOLD,
                'output': buffer_path,
            }),
            AgentStep('clip', {
                'input': layers['communes'],
                'overlay': _layer_name(buffer_path),
                'output': result_path,
            }),
        ],
        assistant_text=(
            "Analyse route/commune (Sénégal) : tampon euclidien de 5 km "
            "autour du réseau routier, puis découpage des communes situées "
            "dans ce périmètre (accessibilité)."
        ),
    )


def build_sen_hydro_proximite(layers: Dict[str, str], out_dir: str) -> AgentPlan:
    buffer_path = os.path.join(out_dir, 'hydro_buffer.gpkg')
    result_path = os.path.join(out_dir, 'zones_proches_hydro.gpkg')
    return AgentPlan(
        steps=[
            AgentStep('buffer', {
                'layer': layers['hydro'],
                'distance': SEN_HYDRO_BUFFER_DISTANCE,
                'output': buffer_path,
            }),
            AgentStep('clip', {
                'input': layers['zones'],
                'overlay': _layer_name(buffer_path),
                'output': result_path,
            }),
        ],
        assistant_text=(
            "Proximité hydrographie (Sénégal) : tampon de 2 km autour des "
            "cours d'eau, puis découpage des zones d'étude dans ce périmètre."
        ),
    )
