"""Balayage des 16 outils SIG (PyQGIS requis).

Usage :
    "C:/Program Files/QGIS 3.44.15/bin/python-qgis-ltr.bat" tests/tools_smoke.py
"""

import os

os.environ.setdefault('TERANGA_OUTPUT_DIR', os.path.join(os.environ.get('TEMP', '.'), 'teranga_tools'))


def _make_layers():
    from qgis.core import (QgsFeature, QgsGeometry, QgsPointXY, QgsProject,
                           QgsVectorLayer)

    pts = QgsVectorLayer('Point?crs=EPSG:32628&field=id:integer&field=cat:string', 'pts', 'memory')
    f1 = QgsFeature(); f1.setGeometry(QgsGeometry.fromPointXY(QgsPointXY(300000, 1600000))); f1.setAttributes([1, 'a'])
    f2 = QgsFeature(); f2.setGeometry(QgsGeometry.fromPointXY(QgsPointXY(301000, 1600500))); f2.setAttributes([2, 'b'])
    pts.dataProvider().addFeatures([f1, f2]); pts.updateExtents()

    poly = QgsVectorLayer('Polygon?crs=EPSG:32628&field=zone:integer', 'zone', 'memory')
    g = QgsGeometry.fromPolygonXY([[
        QgsPointXY(299000, 1599000), QgsPointXY(302000, 1599000),
        QgsPointXY(302000, 1602000), QgsPointXY(299000, 1602000),
    ]])
    fp = QgsFeature(); fp.setGeometry(g); fp.setAttributes([1])
    poly.dataProvider().addFeatures([fp]); poly.updateExtents()

    pts2 = QgsVectorLayer('Point?crs=EPSG:32628&field=id:integer', 'pts2', 'memory')
    f3 = QgsFeature(); f3.setGeometry(QgsGeometry.fromPointXY(QgsPointXY(300500, 1600200))); f3.setAttributes([10])
    pts2.dataProvider().addFeatures([f3]); pts2.updateExtents()

    for layer in (pts, poly, pts2):
        QgsProject.instance().addMapLayer(layer)


def main() -> int:
    try:
        from qgis.PyQt.QtWidgets import QApplication
    except ImportError:
        print("SKIP: qgis non importable (lancer avec python-qgis-ltr.bat)")
        return 0

    app = QApplication.instance() or QApplication([])
    _make_layers()

    from plugin.geofunc.catalog import run_tool

    failures = []

    def check(name, result, expect_ok=True):
        cond = result is not None and result.ok is expect_ok
        detail = '' if cond else f" -> {getattr(result, 'error', None)}"
        print(f"{'PASS' if cond else 'FAIL'} {name}{detail}")
        if not cond:
            failures.append(name)

    check('get_project_info', run_tool('get_project_info', {}))
    check('list_layers', run_tool('list_layers', {}))
    check('get_layer_info', run_tool('get_layer_info', {'name': 'pts'}))
    check('get_selected_features', run_tool('get_selected_features', {}))
    check('reproject_layer', run_tool('reproject_layer', {'layer': 'pts', 'target_crs': 'EPSG:4326'}))
    check('fix_geometries', run_tool('fix_geometries', {'layer': 'pts'}))
    check('remove_duplicates', run_tool('remove_duplicates', {'layer': 'pts', 'fields': ['id']}))
    check('select_by_attribute', run_tool('select_by_attribute', {'layer': 'pts', 'expression': '"id" = 1'}))
    check('buffer', run_tool('buffer', {'layer': 'pts', 'distance': 1000}))
    check('clip', run_tool('clip', {'input': 'pts', 'overlay': 'zone'}))
    check('intersection', run_tool('intersection', {'input': 'zone', 'overlay': 'zone'}))
    check('dissolve', run_tool('dissolve', {'layer': 'zone'}))
    check('spatial_join', run_tool('spatial_join', {'input': 'pts', 'join': 'zone'}))
    check('distance_analysis', run_tool('distance_analysis', {'from': 'pts', 'to': 'pts2'}))
    check('save_layer', run_tool('save_layer', {'layer': 'pts', 'path': os.path.join(os.environ['TERANGA_OUTPUT_DIR'], 'saved_pts.gpkg')}))
    check('export_map (sans iface -> erreur attendue)', run_tool('export_map', {}), expect_ok=False)

    app.quit()
    return 1 if failures else 0


if __name__ == '__main__':
    raise SystemExit(main())