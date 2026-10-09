"""Matching heuristique de couches à partir d'une instruction (S17 — V3 étendu).

Module pur (aucune dépendance QGIS). Extrait des mots-clés de l'instruction,
calcule un score de pertinence entre instruction et des métadonnées de couche,
retourne des candidats classés et le meilleur si suffisamment discriminant.
"""
from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

STOPWORDS = {
    "de", "des", "du", "la", "le", "les", "l", "un", "une", "et", "ou", "sur", "dans", "par", "vers", "au", "aux", "avec", "sans", "pour", "a", "est", "sont", "ce", "cette", "ces", "mon", "ma", "mes", "son", "sa", "ses", "ton", "ta", "tes", "notre", "nos", "votre", "vos", "leur", "leurs", "je", "tu", "il", "elle", "on", "nous", "vous", "ils", "elles", "qui", "que", "quoi", "dont", "où", "ou", "si", "car", "mais", "donc", "or", "ni", "alors", "moi", "toi", "lui", "moi", "toi", "lui", "elle", "se", "me", "te", "nous", "vous", "se", "y", "en", "ce", "ça", "cela", "la", "le", "les", "un", "une", "des", "du", "de", "d", "l", "s", "t", "j", "m", "n", "c", "qu", "p"
}


def normalize(text: str) -> str:
    text = unicodedata.normalize("NFD", text or "")
    text = "".join(ch for ch in text if unicodedata.category(ch) != "Mn")
    return text.lower().strip()


def tokenize(text: str) -> List[str]:
    text = normalize(text)
    tokens = re.findall(r"[a-z0-9_]+", text.replace("-", "_"))
    return [t for t in tokens if t not in STOPWORDS and len(t) > 2]


def jaccard(a: List[str], b: List[str]) -> float:
    sa, sb = set(a), set(b)
    if not sa or not sb:
        return 0.0
    inter = sa & sb
    union = sa | sb
    return len(inter) / len(union) if union else 0.0


@dataclass
class LayerMeta:
    name: str
    geometry_type: Optional[str] = None
    crs: Optional[str] = None
    field_names: List[str] = field(default_factory=list)
    feature_count: Optional[int] = None
    extent: Optional[Dict[str, Any]] = None
    source: Optional[str] = None


@dataclass
class Candidate:
    layer: LayerMeta
    score: float
    reasons: List[str] = field(default_factory=list)


@dataclass
class MatchResult:
    candidates: List[Candidate] = field(default_factory=list)
    best: Optional[Candidate] = None
    ambiguous: bool = False
    reason: Optional[str] = None


def _match_tokens(instruction_tokens: List[str], meta: LayerMeta) -> float:
    score = 0.0
    # name tokens
    name_tokens = tokenize(meta.name)
    j = jaccard(instruction_tokens, name_tokens)
    if j > 0:
        score += j * 0.6
    # field tokens
    field_tokens: List[str] = []
    for fn in meta.field_names:
        field_tokens.extend(tokenize(fn))
    j2 = jaccard(instruction_tokens, field_tokens)
    if j2 > 0:
        score += j2 * 0.25
    # token overlap bonus if any shared tokens
    if j > 0 or j2 > 0:
        pass
    return min(score, 1.0)


def _geometry_hint(instruction: str, geom: Optional[str]) -> float:
    instr = normalize(instruction)
    if not geom:
        return 0.0
    if geom == "Point":
        if any(k in instr for k in ["point", "points", "ville", "villages", "hopital", "hopitaux", "poste", "postes", "localite", "localites"]):
            return 0.15
    if geom == "Line":
        if any(k in instr for k in ["route", "routes", "chemin", "chemins", "troncon", "troncons", "voie", "voies"]):
            return 0.15
    if geom == "Polygon":
        if any(k in instr for k in ["parcelle", "parcelles", "zone", "zones", "commune", "communes", "secteur", "secteurs", "batiment", "batiments", "ilot", "ilots"]):
            return 0.15
    return 0.0


def match_layers(instruction: str, layers: List[LayerMeta]) -> MatchResult:
    """Trouve les couches pertinentes pour une instruction."""
    if not instruction or not instruction.strip() or not layers:
        return MatchResult(candidates=[], best=None, ambiguous=False, reason="aucune instruction ou aucune couche")

    instr_tokens = tokenize(instruction)
    candidates: List[Candidate] = []

    for meta in layers:
        score = _match_tokens(instr_tokens, meta)
        score += _geometry_hint(instruction, meta.geometry_type)
        # substring bonus at match time
        instr_norm = normalize(instruction)
        name_norm = normalize(meta.name)
        if instr_norm and name_norm and (instr_norm in name_norm or name_norm in instr_norm):
            score += 0.3
        reasons: List[str] = []
        if score > 0:
            reasons.append("correspondance lexicale/typée")
        if score == 0:
            continue  # skip weak/no match by default? but keep if only option? handled below
        candidates.append(Candidate(layer=meta, score=min(round(score, 3), 1.0), reasons=reasons))

    # if no candidates found by strong signals, fallback: any layer with any name token overlap tiny? no. but keep empty -> ambiguous
    if not candidates:
        return MatchResult(candidates=[], best=None, ambiguous=True, reason="aucune correspondance claire entre instruction et couches")

    candidates.sort(key=lambda c: c.score, reverse=True)
    best = candidates[0]
    # ambiguous if top scores very close (within 0.1) and >=2 candidates
    if len(candidates) >= 2:
        # if any other candidate has non-trivial overlap/name similarity to best or to query
        second = candidates[1]
        best_name = normalize(best.layer.name)
        second_name = normalize(second.layer.name)
        q = normalize(instruction)
        close = second.score >= best.score - 0.6 or best_name in second_name or second_name in best_name or second_name in q
        if close:
            return MatchResult(candidates=candidates, best=best, ambiguous=True, reason="plusieurs couches candidates proches")
    # ambiguous if best score is low (< 0.3) but exists
    if best.score < 0.3:
        return MatchResult(candidates=candidates, best=best, ambiguous=True, reason="meilleur score faible")
    return MatchResult(candidates=candidates, best=best, ambiguous=False, reason="couche identifiée clairement")
