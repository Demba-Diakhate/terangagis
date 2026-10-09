"""Workflows ciblés Sénégal (S23 complément)."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import List


@dataclass
class SenegalWorkflow:
    name: str
    instructions: List[str] = field(default_factory=list)
    description: str = ""


SEN_WORKFLOWS_EXTRA = [
    SenegalWorkflow(
        name="identification_couche_sen",
        instructions=[
            "rechercher couche par nom (SEN)",
            "vérifier CRS",
            "valider géométrie",
        ],
        description="Identification couche contexte SEN",
    ),
]
