"""Smoke S11 : réutilisation des sorties intermédiaires par nom (PyQGIS requis).

Usage :
    "C:/Program Files/QGIS 3.44.15/bin/python-qgis-ltr.bat" tests/artifacts_smoke.py

Vérifie qu'un plan multi-étapes généré par l'agent peut enchaîner
`buffer` (sortie nommée) → `clip` (référence la sortie par son nom), sans
rechargement manuel, et que les artefacts sont exposés par `/v1/artifacts`.
"""

import os
import sys
import threading
import time

os.environ.setdefault('TERANGA_OUTPUT_DIR', os.path.join(os.environ.get('TEMP', '.'), 'teranga_artifacts_smoke'))


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
    rf.setGeometry(QgsGeometry.fromPolylineXY([QgsPointXY(300000, 1600000), QgsPointXY(303000, 1603000)]))
    rf.setAttributes([1])
    routes.dataProvider().addFeatures([rf])
    routes.updateExtents()

    villages = QgsVectorLayer('Point?crs=EPSG:32628&field=id:integer', 'villages', 'memory')
    feats = []
    for i, (x, y) in enumerate([(300500, 1600500), (360000, 1650000)]):
        f = QgsFeature()
        f.setGeometry(QgsGeometry.fromPointXY(QgsPointXY(x, y)))
        f.setAttributes([i + 1])
        feats.append(f)
    villages.dataProvider().addFeatures(feats)
    villages.updateExtents()

    QgsProject.instance().addMapLayer(routes)
    QgsProject.instance().addMapLayer(villages)

    srv = BridgeServer()
    info = srv.start()
    client = BridgeClient(info['base_url'], info['token'])

    out = {}

    def worker() -> None:
        try:
            out['buffer'] = client.execute('buffer', {
                'layer': 'routes', 'distance': 500, 'output': 'routes_buffer',
            })
            out['clip_by_name'] = client.execute('clip', {
                'input': 'villages', 'overlay': 'routes_buffer', 'output': 'villages_access',
            })
            path = (out['buffer'].get('data') or {}).get('output')
            out['clip_by_path'] = client.execute('clip', {
                'input': 'villages', 'overlay': path,
            })
            out['missing'] = client.execute('clip', {
                'input': 'villages', 'overlay': 'couche_inexistante',
            })
            out['artifacts'] = client.get('/v1/artifacts')
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

    buf = out.get('buffer', {})
    clip_name = out.get('clip_by_name', {})
    clip_path = out.get('clip_by_path', {})
    artifacts = out.get('artifacts', {}).get('data', [])
    names = [a.get('name') for a in artifacts]

    check('worker_termine', not t.is_alive(), out.get('error'))
    check('buffer_ok', buf.get('ok') is True, buf)
    check('buffer_artifact_named', (buf.get('data') or {}).get('artifact') == 'routes_buffer', buf)
    check('clip_by_name_ok', clip_name.get('ok') is True, clip_name)
    check('clip_by_name_artifact', (clip_name.get('data') or {}).get('artifact') == 'villages_access', clip_name)
    check('clip_by_path_ok', clip_path.get('ok') is True, clip_path)
    check('missing_layer_error',
          out.get('missing', {}).get('error', {}).get('code') == 'layer_not_found',
          out.get('missing'))
    check('buffer_layer_in_project', bool(QgsProject.instance().mapLayersByName('routes_buffer')))
    check('clip_layer_in_project', bool(QgsProject.instance().mapLayersByName('villages_access')))
    check('artifacts_listed', 'routes_buffer' in names and 'villages_access' in names, names)
    check('artifacts_metadata', any(a.get('geometry_type') for a in artifacts), artifacts)

    app.quit()
    return 1 if failures else 0


if __name__ == '__main__':
    raise SystemExit(main())
