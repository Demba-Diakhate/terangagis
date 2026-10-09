"""Profilage de données d'une couche (S16 — V3 Data Intelligence).

Module **pur** (aucune dépendance QGIS) : calcule des statistiques élémentaires
et un résumé qualité à partir de valeurs déjà extraites d'une couche. Il est
utilisé côté bridge PyQGIS (extraction des valeurs) et testable hors QGIS.

Convention : `None` représente une valeur nulle (NULL).
"""
from __future__ import annotations

from datetime import date, datetime
from typing import Any, Dict, Iterable, List, Optional

MAX_SAMPLES = 5
SAMPLE_LENGTH = 40
HIGH_NULL_RATIO = 0.5


def _is_number(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def _is_date(value: Any) -> bool:
    return isinstance(value, (date, datetime))


def _iso(value: Any) -> str:
    if _is_date(value):
        return value.isoformat()
    return str(value)


def detect_type(values: Iterable[Any]) -> str:
    """Détecte le type dominant : numeric, text, date, boolean, mixed ou empty."""
    kinds = set()
    for value in values:
        if value is None:
            continue
        if isinstance(value, bool):
            kinds.add("boolean")
        elif _is_number(value):
            kinds.add("numeric")
        elif _is_date(value):
            kinds.add("date")
        elif isinstance(value, str):
            kinds.add("text")
        else:
            kinds.add("other")
    if not kinds:
        return "empty"
    if len(kinds) == 1:
        return next(iter(kinds))
    return "mixed"


def _unique(values: List[Any]) -> List[Any]:
    try:
        return list(dict.fromkeys(values))
    except TypeError:
        seen = set()
        out: List[Any] = []
        for value in values:
            key = repr(value)
            if key not in seen:
                seen.add(key)
                out.append(value)
        return out


def _samples(values: List[Any], max_samples: int) -> List[str]:
    out: List[str] = []
    for value in values[:max_samples]:
        text = str(value)
        if len(text) > SAMPLE_LENGTH:
            text = text[:SAMPLE_LENGTH] + "…"
        out.append(text)
    return out


def profile_field(values: Iterable[Any], max_samples: int = MAX_SAMPLES) -> Dict[str, Any]:
    """Statistiques élémentaires d'un champ à partir de ses valeurs."""
    values = list(values)
    total = len(values)
    non_null = [v for v in values if v is not None]
    null_count = total - len(non_null)
    field_type = detect_type(values)

    out: Dict[str, Any] = {
        "type": field_type,
        "count": total,
        "non_null": len(non_null),
        "null_count": null_count,
        "null_ratio": round(null_count / total, 3) if total else 0.0,
    }

    if field_type == "numeric" and non_null:
        numbers = [float(v) for v in non_null]
        out["min"] = min(numbers)
        out["max"] = max(numbers)
        out["mean"] = round(sum(numbers) / len(numbers), 3)
        out["distinct"] = len(set(non_null))
    elif field_type == "date" and non_null:
        out["min"] = _iso(min(non_null))
        out["max"] = _iso(max(non_null))
        out["distinct"] = len(set(non_null))
    elif field_type == "boolean" and non_null:
        trues = sum(1 for v in non_null if v)
        out["true_count"] = trues
        out["false_count"] = len(non_null) - trues
    elif field_type in ("text", "mixed", "other") and non_null:
        unique = _unique(non_null)
        out["distinct"] = len(unique)
        out["samples"] = _samples(unique, max_samples)

    return out


def _quality_summary(
    field_profiles: Dict[str, Dict[str, Any]],
    *,
    crs: Optional[str],
    feature_count: Optional[int],
    sampled: bool,
    high_null_ratio: float,
) -> Dict[str, Any]:
    high_null = [
        name for name, prof in field_profiles.items()
        if prof["count"] and prof["null_ratio"] >= high_null_ratio
    ]
    empty_fields = [name for name, prof in field_profiles.items() if prof["non_null"] == 0]
    return {
        "field_count": len(field_profiles),
        "missing_crs": not bool(crs),
        "empty": feature_count == 0,
        "sampled": bool(sampled),
        "high_null_ratio": high_null_ratio,
        "high_null_fields": high_null,
        "empty_fields": empty_fields,
    }


def profile_layer(
    fields: Iterable[str],
    values_by_field: Dict[str, Iterable[Any]],
    *,
    geometry_type: Optional[str] = None,
    crs: Optional[str] = None,
    feature_count: Optional[int] = None,
    sampled: bool = False,
    high_null_ratio: float = HIGH_NULL_RATIO,
    max_samples: int = MAX_SAMPLES,
) -> Dict[str, Any]:
    """Profil complet d'une couche : statistiques par champ + résumé qualité."""
    field_profiles: Dict[str, Dict[str, Any]] = {}
    for name in fields:
        field_profiles[name] = profile_field(
            values_by_field.get(name, []), max_samples=max_samples
        )
    out: Dict[str, Any] = {
        "fields": field_profiles,
        "quality": _quality_summary(
            field_profiles,
            crs=crs,
            feature_count=feature_count,
            sampled=sampled,
            high_null_ratio=high_null_ratio,
        ),
    }
    if geometry_type:
        out["geometry_type"] = geometry_type
    if crs is not None:
        out["crs"] = crs
    if feature_count is not None:
        out["feature_count"] = feature_count
    return out


def summarise_profile(profile: Dict[str, Any]) -> str:
    """Résumé textuel court (français) d'un profil, pour l'agent et le panneau."""
    if not profile:
        return "Aucun profil disponible."
    fields = profile.get("fields") or {}
    quality = profile.get("quality") or {}
    parts: List[str] = []
    geom = profile.get("geometry_type")
    if geom:
        parts.append(f"géométrie {geom}")
    parts.append(f"{profile.get('feature_count', '?')} entités")
    parts.append(f"{quality.get('field_count', len(fields))} champs")
    if quality.get("missing_crs"):
        parts.append("CRS manquant")
    high_null = quality.get("high_null_fields") or []
    if high_null:
        parts.append("champs très incomplets : " + ", ".join(high_null))
    if quality.get("empty"):
        parts.append("couche vide")
    return "Profil : " + " ; ".join(parts) + "."
