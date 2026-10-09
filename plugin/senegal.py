"""Exports consolidés Sénégal (S24 — V5 finalisation)."""
from __future__ import annotations

from .senegal_catalog import SenegalCatalog
from .senegal_workflows import SEN_WORKFLOWS
from .senegal_workflows_extra import SEN_WORKFLOWS_EXTRA
from .senegal_helpers import get_sen_sources_summary


__all__ = [
    "SenegalCatalog",
    "SEN_WORKFLOWS",
    "SEN_WORKFLOWS_EXTRA",
    "get_sen_sources_summary",
]
