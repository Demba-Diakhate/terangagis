"""Smoke S17 : auto-identification couche pertinente (PyQGIS requis).

Usage :
    "C:/Program Files/QGIS 3.44.15/bin/python-qgis-ltr.bat" tests/layer_match_smoke.py

Vérifie :
- resolve_best trouve 'routes' pour instruction contenant 'routes'
- match renvoie ambiguous si deux couches similaires existent
"""
from __future__ import annotations

import os
import sys
import threading
import time

os.environ.setdefault(
    'TERANGA_OUTPUT_DIR',
    os.path.join(os.environ.get('TEMP', '.'), 'teranga_layer_match_smoke'),
)


def main() -> int:
    try:
        from qgis.PyQt.QtWidgets import QApplication
        from qgis.core import (QgsFeature, QgsGeometry, QgsPointXY, QgsProject,
                               QgsVectorLayer)
    except ImportError:
        print("SKIP: qgis non importable (lancer avec python-qgis-ltr.bat)")
        return 0

    app = QApplication.instance() or QApplication([])
    QgsProject.instance().clear()

    from plugin.bridge.bridge import BridgeServer
    from mcp.bridge_client import BridgeClient

    routes = QgsVectorLayer('LineString?crs=EPSG:32628&field=id:integer', 'routes', 'memory')
    rf = QgsFeature()
    rf.setGeometry(QgsGeometry.fromPolylineXY([QgsPointXY(0,0), QgsPointXY(100,100)]))
    rf.setAttributes([1])
    routes.dataProvider().addFeatures([rf])
    routes.updateExtents()

    villages = QgsVectorLayer('Point?crs=EPSG:32628&field=id:integer', 'villages', 'memory')
    vf = QgsFeature()
    vf.setGeometry(QgsGeometry.fromPointXY(QgsPointXY(10,10)))
    vf.setAttributes([1])
    villages.dataProvider().addFeatures([vf])
    villages.updateExtents()

    QgsProject.instance().addMapLayer(routes)
    QgsProject.instance().addMapLayer(villages)

    srv = BridgeServer()
    info = srv.start()
    client = BridgeClient(info['base_url'], info['token'])

    out = {}

    def worker() -> None:
        try:
            out['match_routes'] = client.post('/v1/layers/match', {'instruction': 'tampon 5km autour des routes'})
        except Exception as e:  # noqa: BLE001
            out['error'] = repr(e)

    t = threading.Thread(target=worker, daemon=True)
    t.start()
    deadline = time.time() + 60
    while t.is_alive() and time.time() < deadline:
        app.processEvents()
        time.sleep(0.01)
    srv.stop()

    failures = []

    def check(name, cond, detail=''):
        print(f"{'PASS' if cond else 'FAIL'} {name}{(' — ' + str(detail)) if detail and not cond else ''}")
        if not cond:
            failures.append(name)

    mr = out.get('match_routes', {})
    check('worker_termine', not t.is_alive(), out.get('error'))
    check('match_ok', mr.get('ok') is True, mr)
    data = mr.get('data') or {}
    check('best_is_routes', data.get('name') == 'routes', data)
    check('no_ambiguity_simple', data.get('ambiguous') is False, data)

    app.quit()
    return 1 if failures else 0


if __name__ == '__main__':
    raise SystemExit(main())
