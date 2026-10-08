"""Chemins de sortie anti-collision (RT6)."""
from __future__ import annotations

import os
import tempfile
import time


def _is_writable(path: str) -> bool:
    if not os.path.isdir(path):
        return False
    probe = os.path.join(path, '.teranga_write_test')
    try:
        with open(probe, 'w') as fh:
            fh.write('ok')
        os.remove(probe)
        return True
    except OSError:
        return False


def output_dir() -> str:
    base = os.environ.get('TERANGA_OUTPUT_DIR')
    if base:
        try:
            os.makedirs(base, exist_ok=True)
        except OSError:
            pass
        if _is_writable(base):
            return base
    docs = os.path.join(os.path.expanduser('~'), 'Documents')
    if _is_writable(docs):
        return docs
    return tempfile.gettempdir()


def output_path(name: str, ext: str = 'gpkg') -> str:
    """Chemin de sortie horodaté, jamais sur une source du projet (RT6)."""
    ts = time.strftime('%Y%m%d_%H%M%S')
    return os.path.join(output_dir(), f'{name}_teranga_{ts}.{ext}')