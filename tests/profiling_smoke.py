"""Smoke S16 : profilage de données (PyQGIS requis).

Usage :
    "C:/Program Files/QGIS 3.44.15/bin/python-qgis-ltr.bat" tests/profiling_smoke.py

Vérifie :
- get_layer_info(profile=true) retourne un profil avec champs et qualité,
- bridge /v1/layers/<name>/info?profile=true inclut profil et recommandations.
"""
from __future__ import annotations

import os
import sys
import threading
import time

os.environ.setdefault(
    'TERANGA_OUTPUT_DIR',
    os.path.join(os.environ.get('TEMP', '.'), 'teranga_profiling_smoke'),
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

    points = QgsVectorLayer(
        'Point?crs=EPSG:4326&field=id:integer&field=nom:string&field=vide:string',
        'points_test',
        'memory',
    )
    feats = []
    f1 = QgsFeature()
    f1.setGeometry(QgsGeometry.fromPointXY(QgsPointXY(-17.0, 14.7)))
    f1.setAttributes([1, 'Dakar', None])
    feats.append(f1)
    f2 = QgsFeature()
    f2.setGeometry(QgsGeometry.fromPointXY(QgsPointXY(-16.9, 14.8)))
    f2.setAttributes([2, None, None])
    feats.append(f2)
    f3 = QgsFeature()
    f3.setGeometry(QgsGeometry.fromPointXY(QgsPointXY(-16.8, 14.9)))
    f3.setAttributes([3, 'Thiès', None])
    feats.append(f3)
    points.dataProvider().addFeatures(feats)
    points.updateExtents()
    QgsProject.instance().addMapLayer(points)

    srv = BridgeServer()
    info = srv.start()
    client = BridgeClient(info['base_url'], info['token'])

    out = {}

    def worker() -> None:
        try:
            out['tool'] = client.execute('get_layer_info', {'name': 'points_test', 'profile': True})
            out['http'] = client.get('/v1/layers/points_test/info?profile=true')
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

    tool = out.get('tool', {})
    http = out.get('http', {})
    data_tool = tool.get('data') or {}
    data_http = http.get('data') or {}

    check('worker_termine', not t.is_alive(), out.get('error'))
    check('tool_ok', tool.get('ok') is True, tool)
    check('tool_profile_present', 'profile' in data_tool, data_tool)
    check('tool_fields', isinstance(data_tool.get('profile', {}).get('fields'), dict), data_tool)
    check('tool_quality', 'quality' in (data_tool.get('profile') or {}), data_tool)
    check('http_ok', http.get('ok') is True, http)
    check('http_profile_present', 'profile' in data_http, data_http)
    check('http_recommendations_present', 'recommendations' in data_http, data_http)
    check('recs_list', isinstance(data_http.get('recommendations'), list), data_http)

    app.quit()
    return 1 if failures else 0


if __name__ == '__main__':
    raise SystemExit(main())
