"""Extraction des valeurs PyQGIS et construction du profil (S16 — V3).

Ce module dépend de QGIS : il collecte les valeurs des champs d'une couche
vectorielle (avec échantillonnage borné) et délègue le calcul à
`plugin.geofunc.profiling` (module pur).
"""
from __future__ import annotations

from typing import Any, Dict, Optional, Tuple

from qgis.core import QgsVectorLayer

from .profiling import profile_layer

PROFILE_MAX_FEATURES = 5000

_GEOMETRY_NAMES = ['Point', 'Line', 'Polygon', 'Unknown', 'Null']


def _to_python(value: Any) -> Any:
    """Convertit les types QGIS (QDate/QDateTime) en types Python."""
    try:
        from qgis.core import QDate, QDateTime
    except Exception:  # noqa: BLE001
        return value
    if isinstance(value, QDate):
        return value.toPyDate()
    if isinstance(value, QDateTime):
        return value.toPyDateTime()
    return value


def collect_field_values(
    layer: QgsVectorLayer,
    field_names: list[str],
    max_features: int = PROFILE_MAX_FEATURES,
) -> Tuple[Dict[str, list], int, bool]:
    """Collecte les valeurs par champ ; renvoie (valeurs, lues, échantillonné)."""
    values: Dict[str, list] = {name: [] for name in field_names}
    total = layer.featureCount()
    count = 0
    for feature in layer.getFeatures():
        if count >= max_features:
            break
        for name in field_names:
            values[name].append(_to_python(feature[name]))
        count += 1
    sampled = total > count if total >= 0 else False
    return values, count, sampled


def layer_profile(layer: Any, max_features: int = PROFILE_MAX_FEATURES) -> Optional[Dict[str, Any]]:
    """Profil complet d'une couche vectorielle (None si non vectorielle)."""
    if not isinstance(layer, QgsVectorLayer):
        return None
    field_names = [f.name() for f in layer.fields()]
    values, _count, sampled = collect_field_values(layer, field_names, max_features)
    geometry_type = None
    gt = layer.geometryType()
    if 0 <= gt <= 4:
        geometry_type = _GEOMETRY_NAMES[gt]
    crs = layer.crs().authid() if layer.crs().isValid() else ''
    return profile_layer(
        field_names,
        values,
        geometry_type=geometry_type,
        crs=crs,
        feature_count=layer.featureCount(),
        sampled=sampled,
    )
