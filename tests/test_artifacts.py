"""Tests unitaires du registre d'artefacts (S11 — V2).

Purs : aucune dépendance QGIS.
"""
from __future__ import annotations

from plugin.geofunc.artifacts import (
    ArtifactStore,
    logical_name_for_path,
    looks_like_path,
)


def test_logical_name_strips_timestamp_and_extension():
    assert logical_name_for_path('/tmp/routes_buffer_teranga_20261009_031500.gpkg') == 'routes_buffer'
    assert logical_name_for_path('villages.gpkg') == 'villages'
    assert logical_name_for_path('') == 'artifact'


def test_looks_like_path():
    assert looks_like_path('/tmp/out.gpkg') is True
    assert looks_like_path('C:\\\\data\\\\out.gpkg') is True
    assert looks_like_path('resultats_terangagis.gpkg') is True
    assert looks_like_path('routes_buffer') is False
    assert looks_like_path('gps_nettoye') is False


def test_register_and_resolve():
    store = ArtifactStore()
    art = store.register('routes_buffer', '/tmp/a.gpkg', tool='buffer', crs='EPSG:32628')
    assert art.name == 'routes_buffer'
    assert store.resolve('routes_buffer') is art
    assert store.resolve('/tmp/a.gpkg') is art
    assert store.resolve('inconnu') is None
    assert store.names() == ['routes_buffer']
    assert len(store) == 1


def test_register_without_name_derives_from_path():
    store = ArtifactStore()
    art = store.register(None, '/tmp/clip_teranga_20261009_031500.gpkg')
    assert art.name == 'clip'


def test_collision_gets_unique_suffix():
    store = ArtifactStore()
    first = store.register('out', '/tmp/out1.gpkg')
    second = store.register('out', '/tmp/out2.gpkg')
    assert first.name == 'out'
    assert second.name == 'out_2'
    assert store.unique_name('out') == 'out_3'
    assert store.resolve('out') is first
    assert store.resolve('out_2') is second


def test_aliases_resolve_to_same_artifact():
    store = ArtifactStore()
    art = store.register('routes_buffer', '/tmp/a.gpkg', aliases=['rb'])
    assert store.resolve('rb') is art
    assert 'rb' in art.aliases


def test_list_and_clear():
    store = ArtifactStore()
    store.register('a', '/tmp/a.gpkg', tool='buffer')
    store.register('b', '/tmp/b.gpkg', tool='clip')
    listed = store.list()
    assert [item['name'] for item in listed] == ['a', 'b']
    assert listed[0]['tool'] == 'buffer'
    store.clear()
    assert store.names() == []
    assert len(store) == 0
