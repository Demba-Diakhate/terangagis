"""Exécution d'algorithmes QGIS Processing (Processing-first, RT1)."""
from __future__ import annotations
import os
from typing import Any
from qgis.core import QgsProcessingContext, QgsProcessingFeedback
from qgis import processing
def run_processing(alg: str, params: dict[str, Any]) -> dict[str, Any]:
    ctx = QgsProcessingContext()
    fb = QgsProcessingFeedback()
    try:
        return processing.run(alg, params, context=ctx, feedback=fb)
    except Exception:
        raise
