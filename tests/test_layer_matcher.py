"""Tests unitaires du matcher de couches (S17 — V3 étendu)."""
from __future__ import annotations

from plugin.geofunc.layer_matcher import LayerMeta, match_layers, normalize, tokenize


def test_normalize_and_tokenize():
    assert normalize("Routes 5km") == "routes 5km"
    assert tokenize("Tampon de 5 km autour des routes") == ["tampon", "autour", "routes"]
    assert "km" not in " ".join(tokenize("5 km"))
    assert "des" not in tokenize("des villages")


def test_match_routes_prefers_line():
    l1 = LayerMeta(name="routes", geometry_type="Line")
    l2 = LayerMeta(name="villages", geometry_type="Point")
    res = match_layers("créer un tampon de 5 km autour des routes", [l1, l2])
    assert res.best is not None
    assert res.best.layer.name == "routes"
    assert res.ambiguous is False


def test_match_points_villages():
    l1 = LayerMeta(name="villages", geometry_type="Point", field_names=["id", "nom"])
    l2 = LayerMeta(name="routes", geometry_type="Line")
    res = match_layers("villages dans le tampon", [l1, l2])
    assert res.best and res.best.layer.name == "villages"


def test_match_polygon_parcelles():
    l1 = LayerMeta(name="parcelles", geometry_type="Polygon")
    res = match_layers("sélectionner parcelles", [l1])
    assert res.best and res.best.layer.name == "parcelles"


def test_ambiguous_when_similar_names():
    l1 = LayerMeta(name="routes", geometry_type="Line")
    l2 = LayerMeta(name="routes_principales", geometry_type="Line")
    res = match_layers("routes", [l1, l2])
    assert res.ambiguous is True
    assert res.best is not None


def test_ambiguous_when_two_generic():
    l1 = LayerMeta(name="parcelles_a", geometry_type="Polygon")
    l2 = LayerMeta(name="parcelles_b", geometry_type="Polygon")
    res = match_layers("parcelles", [l1, l2])
    assert res.ambiguous is True


def test_no_match_or_weak_returns_ambiguous():
    l1 = LayerMeta(name="batiments", geometry_type="Polygon")
    res = match_layers("routes", [l1])
    assert res.best is None or res.ambiguous is True


def test_fields_improve_score():
    l1 = LayerMeta(name="couches", geometry_type="Point", field_names=["nom_village"])
    l2 = LayerMeta(name="autre", geometry_type="Point", field_names=["code"])
    res = match_layers("villages", [l1, l2])
    assert res.best and res.best.layer.name == "couches"
