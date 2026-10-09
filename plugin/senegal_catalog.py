"""Catalogue de sources géospatiales pour le Sénégal (S22 — V5 GeoAI Sénégal)."""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional


@dataclass
class Source:
    id: str
    name: str
    type: str
    geometry: Optional[str] = None
    description: str = ""
    keywords: List[str] = field(default_factory=list)
    suggested_crs: Optional[str] = None


@dataclass
class SenegalCatalog:
    region: str = "Sénégal"
    sources: List[Source] = field(default_factory=list)

    @classmethod
    def load_default(cls) -> "SenegalCatalog":
        p = Path(__file__).parent / "data" / "senegal_sources.json"
        if not p.exists():
            return cls()
        with p.open('r', encoding='utf-8') as f:
            data = json.load(f)
        sources = [Source(**s) for s in data.get('sources', [])]
        return cls(region=data.get('region', "Sénégal"), sources=sources)

    def find(self, query: str) -> List[Source]:
        q = (query or "").lower()
        res: List[Source] = []
        for s in self.sources:
            if q in s.name.lower() or q in s.description.lower() or any(q in k.lower() for k in s.keywords):
                res.append(s)
        return res
