"""Tests catalogue Sénégal (S22)."""
from __future__ import annotations

from plugin.senegal_catalog import SenegalCatalog


def test_load_and_find():
    cat = SenegalCatalog.load_default()
    assert cat.region == "Sénégal"
    assert len(cat.sources) >= 2
    assert cat.find("route")
    assert cat.find("communes")
