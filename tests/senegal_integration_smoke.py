"""Smoke d'intégration du socle Sénégal (S25) sur mini-jeux synthétiques (PyQGIS).

Jeux de données de test (CRS EPSG:32628, UTM 28N — mètres) :
- `routes`  : 1 ligne  de (300000,1600000) à (305000,1600000)
- `communes`: 2 polygones — 1 traversant le tampon 5 km, 1 éloigné (~40 km)
- `hydro`   : 1 ligne de (300000,1700000) à (302000,1700000)
- `zones`   : 2 polygones — 1 à < 2 km de l'hydro, 1 éloigné (~20 km)

Usage :
    "C:/Program Files/QGIS 3.44.15/bin/python-qgis-ltr.bat" tests/senegal_integration_smoke.py
"""
import os

os.environ.setdefault('TERANGA_OUTPUT_DIR', os.path.join(os.environ.get('TEMP', '.'), 'teranga_sen'))


def _rect(xmin, ymin, xmax, ymax):
    from qgis.core import QgsGeometry, QgsRectangle
    return QgsGeometry.fromRect(QgsRectangle(xmin, ymin, xmax, ymax))


def _make_layers():
    from qgis.core import (QgsFeature, QgsGeometry, QgsPointXY, QgsProject,
                           QgsVectorLayer)

    routes = QgsVectorLayer('LineString?crs=EPSG:32628&field=id:integer', 'routes', 'memory')
    line = QgsFeature()
    line.setGeometry(QgsGeometry.fromPolylineXY([
        QgsPointXY(300000, 1600000), QgsPointXY(305000, 1600000),
    ]))
    line.setAttributes([1])
    routes.dataProvider().addFeatures([line])
    routes.updateExtents()

    communes = QgsVectorLayer('Polygon?crs=EPSG:32628&field=id:integer&field=nom:string',
                              'communes', 'memory')
    cf = []
    near = QgsFeature()
    near.setGeometry(_rect(301000, 1599000, 303000, 1601000))
    near.setAttributes([1, 'proche'])
    far = QgsFeature()
    far.setGeometry(_rect(340000, 1600000, 342000, 1602000))
    far.setAttributes([2, 'eloignee'])
    cf.extend([near, far])
    communes.dataProvider().addFeatures(cf)
    communes.updateExtents()

    hydro = QgsVectorLayer('LineString?crs=EPSG:32628&field=id:integer', 'hydro', 'memory')
    wline = QgsFeature()
    wline.setGeometry(QgsGeometry.fromPolylineXY([
        QgsPointXY(300000, 1700000), QgsPointXY(302000, 1700000),
    ]))
    wline.setAttributes([1])
    hydro.dataProvider().addFeatures([wline])
    hydro.updateExtents()

    zones = QgsVectorLayer('Polygon?crs=EPSG:32628&field=id:integer&field=nom:string',
                           'zones', 'memory')
    zf = []
    z_near = QgsFeature()
    z_near.setGeometry(_rect(300500, 1699500, 301500, 1700500))
    z_near.setAttributes([1, 'proche_hydro'])
    z_far = QgsFeature()
    z_far.setGeometry(_rect(300000, 1720000, 302000, 1721000))
    z_far.setAttributes([2, 'eloignee_hydro'])
    zf.extend([z_near, z_far])
    zones.dataProvider().addFeatures(zf)
    zones.updateExtents()

    for layer in (routes, communes, hydro, zones):
        QgsProject.instance().addMapLayer(layer)


def _count(path):
    from qgis.core import QgsVectorLayer
    layer = QgsVectorLayer(path, 'check', 'ogr')
    return layer.featureCount() if layer.isValid() else -1


def main() -> int:
    try:
        from qgis.PyQt.QtWidgets import QApplication
    except ImportError:
        print("SKIP: qgis non importable (lancer avec python-qgis-ltr.bat)")
        return 0

    app = QApplication.instance() or QApplication([])
    _make_layers()

    from plugin.geofunc.paths import output_dir
    from plugin.geofunc.tools_senegal import FindSenegalSources
    from plugin.workflows import execute_workflow, get_workflow

    out_dir = output_dir()
    failures = []

    def check(name, cond, detail=''):
        print(f"{'PASS' if cond else 'FAIL'} {name}{(' — ' + str(detail)) if detail and not cond else ''}")
        if not cond:
            failures.append(name)

    # 1) Outil find_senegal_sources (pur)
    res = FindSenegalSources().run({})
    check('catalogue_ok', res.ok and res.data['count'] >= 3, res.data if not res.ok else '')
    check('catalogue_ids', {'sen_communes', 'sen_routes', 'sen_hydro'} <=
          {s['id'] for s in res.data['sources']})
    res_route = FindSenegalSources().run({'query': 'route'})
    check('catalogue_query_route', res_route.ok and res_route.data['count'] >= 1)

    # 2) Workflow sen_route_commune : tampon 5 km + découpage communes
    w = get_workflow('sen_route_commune')
    rep = execute_workflow(w, {'routes': 'routes', 'communes': 'communes'}, out_dir)
    check('sen_route_plan_ok', rep.ok, [(s.tool, s.error) for s in rep.steps if not s.ok])
    check('sen_route_outputs_exist', all(os.path.exists(p) for p in rep.outputs), rep.outputs)
    final = rep.outputs[-1] if rep.outputs else ''
    check('sen_route_communes_filtrees', _count(final) == 1, _count(final))

    # 3) Workflow sen_hydro_proximite : tampon 2 km + découpage zones
    w = get_workflow('sen_hydro_proximite')
    rep = execute_workflow(w, {'hydro': 'hydro', 'zones': 'zones'}, out_dir)
    check('sen_hydro_plan_ok', rep.ok, [(s.tool, s.error) for s in rep.steps if not s.ok])
    final = rep.outputs[-1] if rep.outputs else ''
    check('sen_hydro_zones_filtrees', _count(final) == 1, _count(final))

    app.quit()
    return 1 if failures else 0


if __name__ == '__main__':
    raise SystemExit(main())
