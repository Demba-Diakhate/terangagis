"""Outil de recherche dans le catalogue de sources Sénégal (S25 — intégration V5→V6).

Module pur : aucune dépendance QGIS (le catalogue est du métadonnées ; les
couches réelles sont chargées par l'utilisateur dans son projet).
"""
from __future__ import annotations

from typing import Any

from ..senegal_catalog import SenegalCatalog
from .tool_base import GeoTool, ToolResult


class FindSenegalSources(GeoTool):
    name = "find_senegal_sources"
    category = "read"
    description = (
        "Catalogue de sources de données géospatiales recommandées pour le "
        "Sénégal (communes, réseau routier, hydrographie) : métadonnées, mots-clés "
        "et CRS suggéré (EPSG:32628). Paramètre `query` facultatif (mot-clé, "
        "ex. 'route', 'commune', 'hydro') ; sans query, toutes les sources sont "
        "listées. Le catalogue ne fournit que des métadonnées : l'utilisateur "
        "doit charger les couches dans le projet."
    )

    def run(self, params: dict[str, Any]) -> ToolResult:
        catalog = SenegalCatalog.load_default()
        query = str(params.get('query') or '').strip()
        sources = catalog.find(query) if query else list(catalog.sources)
        return ToolResult(ok=True, data={
            'region': catalog.region,
            'query': query,
            'count': len(sources),
            'sources': [
                {
                    'id': s.id,
                    'name': s.name,
                    'type': s.type,
                    'geometry': s.geometry,
                    'description': s.description,
                    'keywords': list(s.keywords),
                    'suggested_crs': s.suggested_crs,
                }
                for s in sources
            ],
        })
