from __future__ import annotations
from typing import Any
from qgis.core import QgsProject, QgsVectorLayer
from .tool_base import GeoTool, ToolResult
from .processing_runner import run_processing
import os, time
def _out_path(name: str) -> str:
    ts = time.strftime("%Y%m%d_%H%M%S")
    return f"{name}_{ts}.gpkg"
class ReprojectLayer(GeoTool):
    name = "reproject_layer"
    def run(self, params: dict[str, Any]) -> ToolResult:
        layer = params.get('layer') or params.get('input')
        target = params.get('target_crs') or params.get('crs')
        if not layer or not target: return ToolResult(ok=False,error={'code':'missing_param','message':"'layer' et 'target_crs' requis"})
        lyr = QgsProject.instance().mapLayersByName(str(layer))
        if not lyr: return ToolResult(ok=False,error={'code':'layer_not_found','message':f'Couche introuvable: {layer}'})
        out = params.get('output') or os.path.join(os.path.expanduser('~'), 'Documents', _out_path('reprojected'))
        res = run_processing('native:reprojectlayer', {'INPUT': lyr[0], 'TARGET_CRS': str(target), 'OUTPUT': out})
        return ToolResult(ok=True,data={'output': res.get('OUTPUT')})
class FixGeometries(GeoTool):
    name = "fix_geometries"
    def run(self, params: dict[str, Any]) -> ToolResult:
        layer = params.get('layer') or params.get('input')
        if not layer: return ToolResult(ok=False,error={'code':'missing_param','message':"'layer' requis"})
        lyr = QgsProject.instance().mapLayersByName(str(layer))
        if not lyr: return ToolResult(ok=False,error={'code':'layer_not_found','message':f'Couche introuvable: {layer}'})
        out = params.get('output') or os.path.join(os.path.expanduser('~'), 'Documents', _out_path('fixed'))
        res = run_processing('native:fixgeometries', {'INPUT': lyr[0], 'OUTPUT': out})
        return ToolResult(ok=True,data={'output': res.get('OUTPUT')})
class RemoveDuplicates(GeoTool):
    name = "remove_duplicates"
    def run(self, params: dict[str, Any]) -> ToolResult:
        layer = params.get('layer') or params.get('input')
        if not layer: return ToolResult(ok=False,error={'code':'missing_param','message':"'layer' requis"})
        lyr = QgsProject.instance().mapLayersByName(str(layer))
        if not lyr: return ToolResult(ok=False,error={'code':'layer_not_found','message':f'Couche introuvable: {layer}'})
        fields = params.get('fields') or []
        out = params.get('output') or os.path.join(os.path.expanduser('~'), 'Documents', _out_path('dedup'))
        res = run_processing('native:removeduplicatesbyattribute', {'INPUT': lyr[0], 'FIELDS': fields, 'OUTPUT': out})
        return ToolResult(ok=True,data={'output': res.get('OUTPUT')})
class SelectByAttribute(GeoTool):
    name = "select_by_attribute"
    def run(self, params: dict[str, Any]) -> ToolResult:
        layer = params.get('layer') or params.get('input')
        expr = params.get('expression') or params.get('where')
        if not layer or not expr: return ToolResult(ok=False,error={'code':'missing_param','message':"'layer' et 'expression' requis"})
        lyr = QgsProject.instance().mapLayersByName(str(layer))
        if not lyr: return ToolResult(ok=False,error={'code':'layer_not_found','message':f'Couche introuvable: {layer}'})
        l = lyr[0]
        if isinstance(l, QgsVectorLayer):
            l.selectByExpression(str(expr))
        return ToolResult(ok=True,data={'selected_count': l.selectedFeatureCount() if isinstance(l,QgsVectorLayer) else 0})
