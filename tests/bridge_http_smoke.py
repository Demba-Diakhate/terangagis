"""Smoke intégration bridge HTTP + outils SIG (PyQGIS requis).

Usage :
    "C:/Program Files/QGIS 3.44.15/bin/python-qgis-ltr.bat" tests/bridge_http_smoke.py

Lance le bridge sur le thread principal, exécute des requêtes HTTP depuis un
thread worker et pompe la boucle Qt pour valider le marshalling inter-threads.
"""

import os
import sys
import threading
import time

os.environ.setdefault('TERANGA_OUTPUT_DIR', os.path.join(os.environ.get('TEMP', '.'), 'teranga_smoke'))


def main() -> int:
    try:
        from qgis.PyQt.QtWidgets import QApplication
        from qgis.core import QgsFeature, QgsGeometry, QgsPointXY, QgsProject, QgsVectorLayer
    except ImportError:
        print("SKIP: qgis non importable (lancer avec python-qgis-ltr.bat)")
        return 0

    app = QApplication.instance() or QApplication([])

    from plugin.bridge.bridge import BridgeServer
    from mcp.bridge_client import BridgeClient

    lyr = QgsVectorLayer('Point?crs=EPSG:32628&field=id:integer', 'pts_smoke', 'memory')
    feat = QgsFeature()
    feat.setGeometry(QgsGeometry.fromPointXY(QgsPointXY(300000, 1600000)))
    feat.setAttributes([1])
    lyr.dataProvider().addFeatures([feat])
    lyr.updateExtents()
    QgsProject.instance().addMapLayer(lyr)

    srv = BridgeServer()
    info = srv.start()
    client = BridgeClient(info['base_url'], info['token'])
    bad = BridgeClient(info['base_url'], 'wrong-token')

    out = {}

    def worker() -> None:
        try:
            out['health'] = client.health()
            out['tools'] = client.list_tools()
            out['layers'] = client.get('/v1/layers')
            out['info'] = client.get('/v1/layers/pts_smoke/info')
            out['exec'] = client.execute('get_project_info', {})
            out['buffer'] = client.execute('buffer', {'layer': 'pts_smoke', 'distance': 500})
            out['unknown_tool'] = client.execute('does_not_exist', {})
            out['bad_layer'] = client.execute('get_layer_info', {'name': 'nope'})
            out['unauthorized'] = bad.health()
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

    check('worker_termine', not t.is_alive(), out.get('error'))
    check('health', out.get('health', {}).get('ok') is True)
    check('tools_count_17', len(out.get('tools', {}).get('data', [])) == 17)
    check('layers', any(l['name'] == 'pts_smoke' for l in out.get('layers', {}).get('data', [])))
    check('layer_info', out.get('info', {}).get('ok') is True)
    check('inspect_exec', out.get('exec', {}).get('ok') is True)
    check('buffer', out.get('buffer', {}).get('ok') is True, out.get('buffer'))
    check('unknown_tool', out.get('unknown_tool', {}).get('error', {}).get('code') == 'tool_not_found')
    check('bad_layer', out.get('bad_layer', {}).get('error', {}).get('code') == 'layer_not_found')
    check('unauthorized', out.get('unauthorized', {}).get('error', {}).get('code') == 'unauthorized')

    app.quit()
    return 1 if failures else 0


if __name__ == '__main__':
    raise SystemExit(main())