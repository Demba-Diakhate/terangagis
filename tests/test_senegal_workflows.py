"""Tests workflows Sénégal (S22)."""
from __future__ import annotations

from plugin.senegal_workflows import SEN_WORKFLOWS


def test_workflows_sen():
    assert len(SEN_WORKFLOWS) >= 1
    assert any(w.name == "analyser_route_commune" for w in SEN_WORKFLOWS)
