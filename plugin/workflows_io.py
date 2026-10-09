"""Chargement/sauvegarde de workflows réutilisables (S20 — V4 Automation).

Format simple : JSON
{
  "name": "...",
  "description": "...",
  "instructions": ["instr1", "instr2"]
}
"""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import List


@dataclass
class Workflow:
    name: str
    description: str = ""
    instructions: List[str] = None  # type: ignore

    def __post_init__(self):
        if self.instructions is None:
            self.instructions = []


class WorkflowIO:
    @staticmethod
    def save(workflow: Workflow, path: str | Path) -> Path:
        p = Path(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        data = asdict(workflow)
        with p.open('w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        return p

    @staticmethod
    def load(path: str | Path) -> Workflow:
        p = Path(path)
        with p.open('r', encoding='utf-8') as f:
            data = json.load(f)
        return Workflow(
            name=data.get('name', p.stem),
            description=data.get('description', ''),
            instructions=data.get('instructions', []) or [],
        )
