"""Smoke des 3 workflows métier (S08) sur des jeux de données documentés (PyQGIS).

Jeux de données de test (CRS EPSG:32628, UTM 28N — mètres) :
- `routes`   : 1 ligne  de (300000,1600000) à (305000,1600000)
- `villages` : 3 points — 2 proches de la route (< 5 km), 1 éloigné (> 40 km)
- `sante`    : 2 points — 1 proche des villages, 1 éloigné
- `gps`      : 4 points — identifiants [1, 1, 2, 3] (1 doublon sur `id`)

Usage :
    "C:/Program Files/QGIS 3.44.15/bin/python-qgis-ltr.bat" tests/workflows_smoke.py
"""
import os

os.environ.setdefault('TERANGA_OUTPUT_DIR', os.path.join(os.environ.get('TEMP', '.'), 'teranga_workflows'))


def _make_layers():
    from qgis.core import (QgsFeature, QgsGeometry, QgsPointXY, QgsProject,
                           QgsVectorLayer)

    routes = QgsVectorLayer('LineString?crs=EPSG:32628&field=id:integer', 'routes', 'memory')
    line = QgsFeature()
    line.setGeometry(QgsGeometry.fromPolylineXY([QgsPointXY(300000, 1600000), QgsPointXY(305000, 1600000)]))
    line.setAttributes([1])
    routes.dataProvider().addFeatures([line]); routes.updateExtents()

    villages = QgsVectorLayer('Point?crs=EPSG:32628&field=id:integer&field=nom:string', 'villages', 'memory')
    vf = []
    for i, (x, y, nom) in enumerate([
        (301000, 1601000, 'proche1'),
        (300500, 1600500, 'proche2'),
        (340000, 1601000, 'eloigne'),
    ], start=1):
        f = QgsFeature(); f.setGeometry(QgsGeometry.fromPointXY(QgsPointXY(x, y))); f.setAttributes([i, nom])
        vf.append(f)
    villages.dataProvider().addFeatures(vf); villages.updateExtents()

    sante = QgsVectorLayer('Point?crs=EPSG:32628&field=id:integer', 'sante', 'memory')
    sf = []
    for i, (x, y) in enumerate([(301500, 1601000), (330000, 1601000)], start=1):
        f = QgsFeature(); f.setGeometry(QgsGeometry.fromPointXY(QgsPointXY(x, y))); f.setAttributes([i])
        sf.append(f)
    sante.dataProvider().addFeatures(sf); sante.updateExtents()

    gps = QgsVectorLayer('Point?crs=EPSG:32628&field=id:integer', 'gps', 'memory')
    gf = []
    for x, y, gid in [(300100, 1600100, 1), (300100, 1600100, 1), (300200, 1600200, 2), (300300, 1600300, 3)]:
        f = QgsFeature(); f.setGeometry(QgsGeometry.fromPointXY(QgsPointXY(x, y))); f.setAttributes([gid])
        gf.append(f)
    gps.dataProvider().addFeatures(gf); gps.updateExtents()

    for layer in (routes, villages, sante, gps):
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
    from plugin.workflows import execute_workflow, get_workflow

    out_dir = output_dir()
    failures = []

    def check(name, cond, detail=''):
        print(f"{'PASS' if cond else 'FAIL'} {name}{(' — ' + str(detail)) if detail and not cond else ''}")
        if not cond:
            failures.append(name)

    # 1) Accessibilité aux routes
    w = get_workflow('road_accessibility')
    rep = execute_workflow(w, {'routes': 'routes', 'villages': 'villages'}, out_dir)
    check('routes_plan_ok', rep.ok, [(s.tool, s.error) for s in rep.steps if not s.ok])
    check('routes_outputs_exist', all(os.path.exists(p) for p in rep.outputs), rep.outputs)
    final = rep.outputs[-1] if rep.outputs else ''
    check('routes_villages_filtres', _count(final) == 2, _count(final))

    # 2) Nettoyage GPS
    w = get_workflow('gps_cleanup')
    rep = execute_workflow(w, {'gps': 'gps'}, out_dir)
    check('gps_plan_ok', rep.ok, [(s.tool, s.error) for s in rep.steps if not s.ok])
    clean = rep.outputs[-2] if len(rep.outputs) >= 2 else ''
    check('gps_doublons_supprimes', _count(clean) == 3, _count(clean))
    check('gps_export_final', os.path.exists(rep.outputs[-1]) if rep.outputs else False)

    # 3) Accessibilité aux postes de santé
    w = get_workflow('health_accessibility')
    rep = execute_workflow(w, {'villages': 'villages', 'sante': 'sante'}, out_dir)
    check('sante_plan_ok', rep.ok, [(s.tool, s.error) for s in rep.steps if not s.ok])
    matrix = rep.outputs[0] if rep.outputs else ''
    check('sante_matrice_distances', _count(matrix) == 6, _count(matrix))

    app.quit()
    return 1 if failures else 0


if __name__ == '__main__':
    raise SystemExit(main())