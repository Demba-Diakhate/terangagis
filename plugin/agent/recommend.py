"""Recommandations d'analyses à partir d'un profil de couche (S16 — V3).

Module **pur** (aucune dépendance QGIS) : dérive des suggestions d'analyses
génériques et dédupliquées à partir du profil produit par
`plugin.geofunc.profiling.profile_layer`.

Les recommandations sont déterministes et classées par priorité. Elles portent
chacune : `code` (identifiant unique), `title`, `reason`, `tools` (outils SIG
suggérés, noms MCP) et `priority` (plus petit = plus prioritaire).
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

_POLYGON = "Polygon"
_LINE = "Line"
_POINT = "Point"

MAX_CATEGORIES = 20


def _field_with(profile: Dict[str, Any], field_type: str) -> List[str]:
    return [
        name for name, prof in (profile.get("fields") or {}).items()
        if prof.get("type") == field_type
    ]


def _geographic_crs(crs: Optional[str]) -> bool:
    if not crs:
        return False
    text = str(crs).upper()
    if "4326" in text or "426" in text:
        return True
    if ":" in text:
        try:
            code = int(text.split(":")[-1])
        except ValueError:
            return False
        return 4000 <= code < 5000
    return False


def recommend(profile: Optional[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Suggère des analyses pertinentes, dédupliquées et classées."""
    if not profile:
        return []

    quality = profile.get("quality") or {}
    crs = profile.get("crs")
    geometry_type = profile.get("geometry_type")
    recs: List[Dict[str, Any]] = []

    # Le CRS peut aussi être présent directement dans le profil ou dans quality
    if crs is None:
        crs = quality.get("crs")

    if quality.get("missing_crs") or not crs:
        recs.append({
            "code": "crs_manquant",
            "title": "Définir le CRS",
            "reason": "Le CRS de la couche est indéfini ; les mesures seraient fausses.",
            "tools": ["reproject_layer"],
            "priority": 10,
        })
    elif _geographic_crs(crs):
        recs.append({
            "code": "crs_geographique",
            "title": "Reprojeter en CRS projeté",
            "reason": f"Le CRS {crs} est géographique (degrés) : reprojeter pour les opérations métriques.",
            "tools": ["reproject_layer"],
            "priority": 20,
        })

    if quality.get("empty"):
        recs.append({
            "code": "couche_vide",
            "title": "Vérifier la source",
            "reason": "La couche ne contient aucune entité.",
            "tools": [],
            "priority": 30,
        })

    empty_fields = quality.get("empty_fields") or []
    if empty_fields:
        recs.append({
            "code": "champs_vides",
            "title": "Champs entièrement vides",
            "reason": "Champs sans aucune valeur : " + ", ".join(empty_fields) + ".",
            "tools": ["select_by_attribute"],
            "priority": 40,
        })

    high_null = quality.get("high_null_fields") or []
    if high_null:
        recs.append({
            "code": "valeurs_manquantes",
            "title": "Traiter les valeurs manquantes",
            "reason": "Champs très incomplets : " + ", ".join(high_null) + ".",
            "tools": ["select_by_attribute"],
            "priority": 50,
        })

    numeric_fields = _field_with(profile, "numeric")
    if numeric_fields:
        recs.append({
            "code": "champ_numerique",
            "title": "Filtrer/classifier sur un champ numérique",
            "reason": "Champ(s) numérique(s) exploitable(s) : " + ", ".join(numeric_fields) + ".",
            "tools": ["select_by_attribute"],
            "priority": 60,
        })

    categorical = [
        name for name, prof in (profile.get("fields") or {}).items()
        if prof.get("type") == "text" and 1 < prof.get("distinct", 0) <= MAX_CATEGORIES
    ]
    if categorical:
        recs.append({
            "code": "champ_categoriel",
            "title": "Regrouper par catégorie",
            "reason": "Champ(s) catégoriel(s) pour agréger : " + ", ".join(categorical) + ".",
            "tools": ["dissolve"],
            "priority": 70,
        })

    if geometry_type == _POLYGON:
        recs.append({
            "code": "geometrie_polygone",
            "title": "Analyses surfaciques",
            "reason": "Couche polygonale : regrouper (dissolve) ou découper (clip).",
            "tools": ["dissolve", "clip"],
            "priority": 80,
        })
    elif geometry_type == _LINE:
        recs.append({
            "code": "geometrie_ligne",
            "title": "Zones d'accessibilité",
            "reason": "Couche linéaire : créer des tampons (buffer) puis découper (clip).",
            "tools": ["buffer", "clip"],
            "priority": 80,
        })
    elif geometry_type == _POINT:
        recs.append({
            "code": "geometrie_point",
            "title": "Analyses de proximité",
            "reason": "Couche ponctuelle : analyse de distance et jointure spatiale.",
            "tools": ["distance_analysis", "spatial_join"],
            "priority": 80,
        })

    recs.sort(key=lambda r: (r["priority"], r["code"]))
    return recs


def summarise_recommendations(recs: List[Dict[str, Any]]) -> str:
    """Résumé textuel court (français) des recommandations, pour le panneau."""
    if not recs:
        return ""
    lines = [f"- {r['title']} : {r['reason']}" for r in recs]
    return "Recommandations :\n" + "\n".join(lines)
