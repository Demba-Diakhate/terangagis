"""Exécution d'algorithmes QGIS Processing (Processing-first, RT1)."""
from __future__ import annotations

import os
import sys

from typing import Any

from qgis.core import QgsProcessingContext, QgsProcessingFeedback

_initialized = False


def _ensure_processing() -> None:
    global _initialized
    if _initialized:
        return
    try:
        import qgis  # noqa: F401
        plugins_dir = os.path.join(os.path.dirname(os.path.dirname(qgis.__file__)), 'plugins')
        if os.path.isdir(plugins_dir) and plugins_dir not in sys.path:
            sys.path.append(plugins_dir)
    except Exception:
        pass
    try:
        from processing.core.Processing import Processing
        Processing.initialize()
    except Exception:
        pass
    _initialized = True


def run_processing(alg: str, params: dict[str, Any]) -> dict[str, Any]:
    _ensure_processing()
    from qgis import processing
    ctx = QgsProcessingContext()
    fb = QgsProcessingFeedback()
    return processing.run(alg, params, context=ctx, feedback=fb)