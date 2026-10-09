"""Tests unitaires du profilage de données (S16 — V3 Data Intelligence).

Purs : aucune dépendance QGIS.
"""
from __future__ import annotations

from datetime import date

from plugin.geofunc.profiling import (
    detect_type,
    profile_field,
    profile_layer,
    summarise_profile,
)


def test_profile_numeric_field():
    prof = profile_field([1, 2, 3, None])
    assert prof['type'] == 'numeric'
    assert prof['count'] == 4
    assert prof['non_null'] == 3
    assert prof['null_count'] == 1
    assert prof['null_ratio'] == 0.25
    assert prof['min'] == 1.0
    assert prof['max'] == 3.0
    assert prof['mean'] == 2.0
    assert prof['distinct'] == 3


def test_profile_text_field_samples_and_truncation():
    long_value = 'x' * 100
    prof = profile_field(['a', 'b', 'a', long_value])
    assert prof['type'] == 'text'
    assert prof['distinct'] == 3
    assert 'a' in prof['samples']
    assert any(s.endswith('…') for s in prof['samples'])


def test_profile_date_field():
    prof = profile_field([None, None, date(2020, 1, 1), date(2021, 6, 1)])
    assert prof['type'] == 'date'
    assert prof['min'].startswith('2020-01-01')
    assert prof['max'].startswith('2021-06-01')


def test_profile_boolean_field():
    prof = profile_field([True, False, True, None])
    assert prof['type'] == 'boolean'
    assert prof['true_count'] == 2
    assert prof['false_count'] == 1


def test_profile_empty_field():
    prof = profile_field([None, None])
    assert prof['type'] == 'empty'
    assert prof['non_null'] == 0
    assert prof['null_ratio'] == 1.0


def test_detect_type_mixed():
    assert detect_type(['a', 1]) == 'mixed'
    assert detect_type([]) == 'empty'
    assert detect_type([1, 2.5]) == 'numeric'


def test_profile_layer_quality_summary():
    profile = profile_layer(
        ['id', 'nom', 'vide'],
        {
            'id': [1, 2, 3],
            'nom': ['a', None, None],
            'vide': [None, None, None],
        },
        geometry_type='Point',
        crs='EPSG:32628',
        feature_count=3,
    )
    quality = profile['quality']
    assert quality['field_count'] == 3
    assert quality['missing_crs'] is False
    assert quality['empty'] is False
    assert 'vide' in quality['empty_fields']
    assert 'nom' in quality['high_null_fields']
    assert profile['geometry_type'] == 'Point'


def test_profile_layer_missing_crs_and_sampling():
    profile = profile_layer(
        ['id'],
        {'id': [1, 2]},
        feature_count=10,
        sampled=True,
    )
    assert profile['quality']['missing_crs'] is True
    assert profile['quality']['sampled'] is True
    assert profile['feature_count'] == 10


def test_summarise_profile():
    profile = profile_layer(
        ['id'],
        {'id': [1, 2]},
        geometry_type='Polygon',
        crs='EPSG:32628',
        feature_count=2,
    )
    text = summarise_profile(profile)
    assert text.startswith('Profil :')
    assert 'Polygon' in text
    assert summarise_profile({}) == "Aucun profil disponible."
