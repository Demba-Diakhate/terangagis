"""Définitions des 3 workflows métier (S08).

Chaque workflow construit un `AgentPlan` à partir d'un mapping de couches
d'entrée (`{rôle: nom_de_couche}`) et d'un répertoire de sortie. Les noms de
couches produits sont dérivés du nom de fichier, ce qui permet d'enchaîner les
étapes (`buffer` → `clip`, etc.).
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Callable, Dict, List

from ..agent.agent import AgentPlan, AgentStep

ROAD_BUFFER_DISTANCE = 5000
HEALTH_DISTANCE_THRESHOLD = 10000


def layer_name_from_path(path: str) -> str:
    return os.path.splitext(os.path.basename(path))[0]


@dataclass
class Workflow:
    key: str
    title: str
    instruction: str
    required_layers: List[str]
    builder: Callable[[Dict[str, str], str], AgentPlan]
    description: str = ''

    def build(self, layers: Dict[str, str], out_dir: str) -> AgentPlan:
        missing = [r for r in self.required_layers if r not in layers]
        if missing:
            raise KeyError(f"Couches manquantes pour '{self.key}': {', '.join(missing)}")
        return self.builder(layers, out_dir)


def build_road_accessibility(layers: Dict[str, str], out_dir: str) -> AgentPlan:
    buffer_path = os.path.join(out_dir, 'acces_routes_buffer.gpkg')
    result_path = os.path.join(out_dir, 'villages_acces_routes.gpkg')
    return AgentPlan(
        steps=[
            AgentStep('buffer', {
                'layer': layers['routes'],
                'distance': ROAD_BUFFER_DISTANCE,
                'output': buffer_path,
            }),
            AgentStep('clip', {
                'input': layers['villages'],
                'overlay': layer_name_from_path(buffer_path),
                'output': result_path,
            }),
        ],
        assistant_text=(
            "Accessibilité aux routes : tampon de 5 km autour des routes, puis "
            "découpage des villages situés dans ce périmètre."
        ),
    )


def build_gps_cleanup(layers: Dict[str, str], out_dir: str) -> AgentPlan:
    fixed_path = os.path.join(out_dir, 'gps_corrige.gpkg')
    clean_path = os.path.join(out_dir, 'gps_nettoye.gpkg')
    final_path = os.path.join(out_dir, 'gps_final.gpkg')
    return AgentPlan(
        steps=[
            AgentStep('fix_geometries', {
                'layer': layers['gps'],
                'output': fixed_path,
            }),
            AgentStep('remove_duplicates', {
                'layer': layer_name_from_path(fixed_path),
                'fields': ['id'],
                'output': clean_path,
            }),
            AgentStep('save_layer', {
                'layer': layer_name_from_path(clean_path),
                'path': final_path,
            }),
        ],
        assistant_text=(
            "Nettoyage des données GPS : correction des géométries, suppression "
            "des doublons sur l'identifiant, puis export du résultat."
        ),
    )


def build_health_accessibility(layers: Dict[str, str], out_dir: str) -> AgentPlan:
    matrix_path = os.path.join(out_dir, 'dist_villages_sante.gpkg')
    return AgentPlan(
        steps=[
            AgentStep('distance_analysis', {
                'from': layers['villages'],
                'to': layers['sante'],
                'output': matrix_path,
            }),
            AgentStep('select_by_attribute', {
                'layer': layer_name_from_path(matrix_path),
                'expression': f'"Distance" > {HEALTH_DISTANCE_THRESHOLD}',
            }),
        ],
        assistant_text=(
            "Accessibilité aux postes de santé : matrice des distances "
            "euclidiennes villages ↔ postes, puis sélection des couples situés "
            "à plus de 10 km."
        ),
    )


WORKFLOWS: List[Workflow] = [
    Workflow(
        key='road_accessibility',
        title='Accessibilité aux routes',
        instruction="Identifie les villages situés à moins de 5 km d'une route.",
        required_layers=['routes', 'villages'],
        builder=build_road_accessibility,
        description="Tampon de 5 km autour des routes, puis découpage des villages.",
    ),
    Workflow(
        key='gps_cleanup',
        title='Nettoyage de données GPS',
        instruction="Nettoie cette couche GPS et corrige les géométries.",
        required_layers=['gps'],
        builder=build_gps_cleanup,
        description="Correction des géométries, suppression des doublons, export.",
    ),
    Workflow(
        key='health_accessibility',
        title='Accessibilité aux postes de santé',
        instruction="Identifie les villages situés à plus de 10 km d'un poste de santé.",
        required_layers=['villages', 'sante'],
        builder=build_health_accessibility,
        description="Distances euclidiennes villages ↔ postes de santé (RT5).",
    ),
]

_BY_KEY = {w.key: w for w in WORKFLOWS}


def get_workflow(key: str) -> Workflow:
    if key not in _BY_KEY:
        raise KeyError(f"Workflow inconnu: {key}")
    return _BY_KEY[key]


def list_workflows() -> List[Dict[str, str]]:
    return [
        {
            'key': w.key,
            'title': w.title,
            'instruction': w.instruction,
            'required_layers': ', '.join(w.required_layers),
            'description': w.description,
        }
        for w in WORKFLOWS
    ]


def build_plan(key: str, layers: Dict[str, str], out_dir: str) -> AgentPlan:
    return get_workflow(key).build(layers, out_dir)