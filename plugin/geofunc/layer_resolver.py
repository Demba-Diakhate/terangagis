"""Résolution d'une référence de couche pour un outil (S11 — V2).

Ordre de résolution : artefact de session → couche du projet (par nom) → chemin
de fichier. La couche résolue est **ajoutée au projet QGIS** sous son nom logique
si elle n'y est pas déjà, afin que les outils existants (qui utilisent
`QgsProject.mapLayersByName`) la retrouvent sans modification.

Les fonctions de ce module doivent s'exécuter sur le thread principal QGIS.
"""
from __future__ import annotations

import os
from typing import Any, Optional

from .artifacts import Artifact, logical_name_for_path

LAYER_PARAM_KEYS = ('layer', 'input', 'overlay', 'join', 'from', 'to')


def _load_vector_layer(path: str, name: str):
    from qgis.core import QgsVectorLayer

    if not path or not os.path.exists(path):
        return None
    layer = QgsVectorLayer(path, name, 'ogr')
    return layer if layer.isValid() else None


def _add_to_project(layer, name: str) -> None:
    from qgis.core import QgsProject

    project = QgsProject.instance()
    if not project.mapLayersByName(name):
        layer.setName(name)
        project.addMapLayer(layer)


def add_artifact_to_project(artifact: Optional[Artifact]) -> bool:
    """Ajoute l'artefact au projet (visible) sous son nom logique. Vrai si présent."""
    if artifact is None or not artifact.path:
        return False
    from qgis.core import QgsProject

    project = QgsProject.instance()
    if project.mapLayersByName(artifact.name):
        return True
    layer = _load_vector_layer(artifact.path, artifact.name)
    if layer is None:
        return False
    _add_to_project(layer, artifact.name)
    return True


def ensure_layer_in_project(value: Any, store: Any = None) -> str:
    """Retourne le **nom de couche du projet** correspondant à `value`.

    Lève `KeyError` si la référence est introuvable ; le bridge la convertit en
    erreur structurée `layer_not_found`.
    """
    from qgis.core import QgsProject

    if value is None or value == '':
        raise KeyError(value)

    project = QgsProject.instance()
    key = str(value)

    artifact = store.resolve(value) if store is not None else None
    if artifact is not None:
        if project.mapLayersByName(artifact.name):
            return artifact.name
        if add_artifact_to_project(artifact):
            return artifact.name

    if project.mapLayersByName(key):
        return key

    if os.path.exists(key):
        name = artifact.name if artifact is not None else logical_name_for_path(key)
        if project.mapLayersByName(name):
            return name
        layer = _load_vector_layer(key, name)
        if layer is not None:
            _add_to_project(layer, name)
            return name

    raise KeyError(key)
