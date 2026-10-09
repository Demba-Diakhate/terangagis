"""Tests unitaires du moteur de recommandations (S16 — V3)."""
from __future__ import annotations

from plugin.agent.recommend import recommend, summarise_recommendations
from plugin.geofunc.profiling import profile_layer


def _profile(**quality_overrides):
    base = {
        'fields': {},
        'quality': {
            'field_count': 0,
            'missing_crs': False,
            'empty': False,
            'sampled': False,
            'high_null_ratio': 0.5,
            'high_null_fields': [],
            'empty_fields': [],
        },
    }
    base['quality'].update(quality_overrides)
    return base


def _codes(recs):
    return [r['code'] for r in recs]


def test_recommend_empty_input():
    assert recommend(None) == []
    assert recommend({}) == []


def test_recommend_missing_crs():
    recs = recommend(_profile(missing_crs=True))
    assert 'crs_manquant' in _codes(recs)


def test_recommend_geographic_crs():
    recs = recommend(_profile(crs='EPSG:4326'))
    assert 'crs_geographique' in _codes(recs)
    assert 'crs_manquant' not in _codes(recs)


def test_no_crs_recommendation_for_projected():
    recs = recommend(_profile(crs='EPSG:32628'))
    assert 'crs_manquant' not in _codes(recs)
    assert 'crs_geographique' not in _codes(recs)


def test_geometry_specific_recommendations():
    assert 'geometrie_polygone' in _codes(recommend(_profile() | {'geometry_type': 'Polygon'}))
    assert 'geometrie_ligne' in _codes(recommend(_profile() | {'geometry_type': 'Line'}))
    assert 'geometrie_point' in _codes(recommend(_profile() | {'geometry_type': 'Point'}))


def test_field_based_recommendations():
    profile = profile_layer(
        ['age', 'region', 'ville'],
        {'age': [10, 20], 'region': ['Dakar', 'Thiès', 'Dakar'], 'ville': ['A', 'B', 'A']},
        geometry_type='Point',
        crs='EPSG:32628',
        feature_count=3,
    )
    codes = _codes(recommend(profile))
    assert 'champ_numerique' in codes
    assert 'champ_categoriel' in codes


def test_high_cardinality_not_categorical():
    profile = profile_layer(
        ['ref'],
        {'ref': [f'r{i}' for i in range(50)]},
        crs='EPSG:32628',
        feature_count=50,
    )
    assert 'champ_categoriel' not in _codes(recommend(profile))


def test_quality_recommendations():
    recs = recommend(_profile(empty=True, empty_fields=['x'], high_null_fields=['y']))
    codes = _codes(recs)
    assert 'couche_vide' in codes
    assert 'champs_vides' in codes
    assert 'valeurs_manquantes' in codes


def test_recommendations_sorted_and_deduplicated():
    profile = profile_layer(
        ['age'],
        {'age': [1, 2]},
        geometry_type='Polygon',
        crs='EPSG:4326',
        feature_count=2,
    )
    recs = recommend(profile)
    codes = _codes(recs)
    assert len(codes) == len(set(codes))
    priorities = [r['priority'] for r in recs]
    assert priorities == sorted(priorities)


def test_summarise_recommendations():
    recs = recommend(_profile(missing_crs=True))
    text = summarise_recommendations(recs)
    assert text.startswith('Recommandations :')
    assert summarise_recommendations([]) == ''
