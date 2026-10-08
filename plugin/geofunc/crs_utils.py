"""Helpers CRS (UTM Sénégal) et unités."""
from __future__ import annotations
from qgis.core import QgsCoordinateReferenceSystem
def suggest_utm_zone(lon: float, lat: float) -> str:
    zone = int((lon + 180) / 6) + 1
    return f"EPSG:326{zone:02d}" if lat >= 0 else f"EPSG:327{zone:02d}"
def is_projected(crs: QgsCoordinateReferenceSystem) -> bool:
    return crs.isValid() and crs.projectionAcronym() != ""
