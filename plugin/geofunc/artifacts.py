"""Réutilisation des sorties intermédiaires (S11 — V2 Workflow Agent).

Registre des artefacts produits par les outils : un **nom logique** est associé
à un chemin de fichier et à ses métadonnées, pour qu'une étape suivante puisse
référencer la sortie d'une étape précédente par son nom (sans rechargement
manuel). Module **pur** (aucune dépendance QGIS) afin d'être testable hors QGIS.
"""
from __future__ import annotations

import os
import re
import threading
from dataclasses import dataclass, field
from typing import Any, Dict, Iterable, List, Optional

_TIMESTAMP_RE = re.compile(r'_teranga_\d{8}_\d{6}$')


def logical_name_for_path(path: str) -> str:
    """Nom logique dérivé d'un chemin (base sans extension, horodatage retiré)."""
    base = os.path.splitext(os.path.basename(str(path)))[0]
    base = _TIMESTAMP_RE.sub('', base)
    return base or 'artifact'


def looks_like_path(value: str) -> bool:
    """Vrai si `value` ressemble à un chemin (séparateur ou extension)."""
    text = str(value)
    if '/' in text or '\\' in text or os.sep in text:
        return True
    if os.altsep and os.altsep in text:
        return True
    return bool(os.path.splitext(text)[1])


@dataclass
class Artifact:
    """Sortie produite par un outil, réutilisable sous un nom logique."""

    name: str
    path: str
    tool: str = ''
    crs: str = ''
    geometry_type: str = ''
    feature_count: int = -1
    step_index: int = -1
    aliases: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            'name': self.name,
            'path': self.path,
            'tool': self.tool,
            'crs': self.crs,
            'geometry_type': self.geometry_type,
            'feature_count': self.feature_count,
            'step_index': self.step_index,
            'aliases': list(self.aliases),
        }


class ArtifactStore:
    """Registre thread-safe des artefacts d'une session d'exécution."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._by_name: Dict[str, Artifact] = {}
        self._by_path: Dict[str, Artifact] = {}

    def _unique_name_locked(self, base: str) -> str:
        base = base or 'artifact'
        if base not in self._by_name:
            return base
        index = 2
        while f'{base}_{index}' in self._by_name:
            index += 1
        return f'{base}_{index}'

    def unique_name(self, base: str) -> str:
        with self._lock:
            return self._unique_name_locked(base)

    def register(
        self,
        name: str | None,
        path: str,
        *,
        tool: str = '',
        crs: str = '',
        geometry_type: str = '',
        feature_count: int = -1,
        step_index: int = -1,
        aliases: Iterable[str] = (),
    ) -> Artifact:
        """Enregistre un artefact ; renomme en `<nom>_2` en cas de collision."""
        path = str(path)
        requested = str(name) if name else logical_name_for_path(path)
        with self._lock:
            final = self._unique_name_locked(requested)
            artifact = Artifact(
                name=final,
                path=path,
                tool=tool,
                crs=crs,
                geometry_type=geometry_type,
                feature_count=feature_count,
                step_index=step_index,
            )
            self._by_name[final] = artifact
            self._by_path[path] = artifact
            for alias in aliases:
                if alias:
                    self._by_name.setdefault(str(alias), artifact)
                    artifact.aliases.append(str(alias))
            return artifact

    def resolve(self, value: Any) -> Optional[Artifact]:
        """Retrouve un artefact par nom logique ou par chemin de fichier."""
        if value is None:
            return None
        key = str(value)
        with self._lock:
            if key in self._by_name:
                return self._by_name[key]
            if key in self._by_path:
                return self._by_path[key]
        return None

    def get(self, name: str) -> Optional[Artifact]:
        return self.resolve(name)

    def names(self) -> List[str]:
        with self._lock:
            return sorted(self._by_name.keys())

    def list(self) -> List[Dict[str, Any]]:
        with self._lock:
            seen: Dict[str, Artifact] = {}
            for artifact in self._by_name.values():
                seen[artifact.name] = artifact
            return [seen[name].to_dict() for name in sorted(seen)]

    def clear(self) -> None:
        with self._lock:
            self._by_name.clear()
            self._by_path.clear()

    def __len__(self) -> int:
        with self._lock:
            return len({a.name for a in self._by_name.values()})
