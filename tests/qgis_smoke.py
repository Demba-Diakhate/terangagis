"""Smoke test PyQGIS — exécutable avec le Python embarqué de QGIS uniquement.

Usage :
    "C:/Program Files/QGIS 3.44.15/bin/python-qgis-ltr.bat" tests/qgis_smoke.py
"""

import sys


def main() -> int:
    try:
        from qgis.core import Qgis, QgsApplication, QgsProject, QgsVectorLayer
    except ImportError:
        print("SKIP: qgis non importable dans cet interpréteur (lancer avec python-qgis-ltr.bat)")
        return 0

    app = QgsApplication([], False)
    app.initQgis()
    version = Qgis.QGIS_VERSION
    print(f"PyQGIS OK — QGIS {version} — Python {sys.version.split()[0]}")

    layer = QgsVectorLayer("Point?crs=EPSG:4326", "smoke", "memory")
    assert layer.isValid(), "couche mémoire invalide"
    assert QgsProject.instance().mapLayersByName("smoke") == []
    print("Création de couche mémoire OK")
    app.exitQgis()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
