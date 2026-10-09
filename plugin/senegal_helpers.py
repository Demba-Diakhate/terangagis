"""V5 enrichment (S23)."""
from __future__ import annotations

from plugin.senegal_catalog import SenegalCatalog


def get_sen_sources_summary() -> str:
    cat = SenegalCatalog.load_default()
    items = "; ".join(f"{s.id}:{s.name}" for s in cat.sources)
    return f"Sénégal ({cat.region}): {items}"
