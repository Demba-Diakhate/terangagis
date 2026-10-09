"""Workflows ciblés Sénégal (S22 — V5 GeoAI Sénégal)."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import List


@dataclass
class SenegalWorkflow:
    name: str
    instructions: List[str] = field(default_factory=list)
    description: str = ""


SEN_WORKFLOWS = [
    SenegalWorkflow(
        name="analyser_route_commune",
        instructions=[
            "identifier communes sénégalaises",
            "charger réseau routier sénégalais",
            "calculer distance route-commune",
        ],
        description="Analyse route/commune (Sénégal)",
    ),
    SenegalWorkflow(
        name="hydro_proximite",
        instructions=[
            "charger hydrographie sénégalaise",
            "sélectionner zones proches cours d'eau",
            "rapporter emprise",
        ],
        description="Proximité hydrographie (Sénégal)",
    ),
]
