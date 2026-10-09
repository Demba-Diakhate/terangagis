"""Tests V5 enrichment (S23)."""
from __future__ import annotations

from plugin.senegal_helpers import get_sen_sources_summary


def test_summary():
    s = get_sen_sources_summary()
    assert "Sénégal" in s
    assert "sen_communes" in s
