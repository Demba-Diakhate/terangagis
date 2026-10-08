from __future__ import annotations
from typing import Any
from qgis.core import QgsProject, QgsVectorLayer
from .tool_base import GeoTool, ToolResult
from .processing_runner import run_processing
from .paths import output_path
class Buffer(GeoTool):
    name = "buffer"
    category = "analyze"
    def run(self, params: dict[str, Any]) -> ToolResult:
        layer = params.get('layer') or params.get('input')
        dist = params.get('distance')
        if not layer or dist is None: return ToolResult(ok=False,error={'code':'missing_param','message':"'layer' et 'distance' requis"})
        lyr = QgsProject.instance().mapLayersByName(str(layer))
        if not lyr: return ToolResult(ok=False,error={'code':'layer_not_found','message':f'Couche introuvable: {layer}'})
        out = params.get('output') or output_path('buffer')
        res = run_processing('native:buffer', {'INPUT': lyr[0], 'DISTANCE': float(dist), 'OUTPUT': out})
        return ToolResult(ok=True,data={'output': res.get('OUTPUT')})
class Clip(GeoTool):
    name = "clip"
    category = "analyze"
    def run(self, params: dict[str, Any]) -> ToolResult:
        input_ = params.get('input') or params.get('layer')
        overlay = params.get('overlay') or params.get('clip')
        if not input_ or not overlay: return ToolResult(ok=False,error={'code':'missing_param','message':"'input' et 'overlay' requis"})
        l1 = QgsProject.instance().mapLayersByName(str(input_)); l2 = QgsProject.instance().mapLayersByName(str(overlay))
        if not l1 or not l2: return ToolResult(ok=False,error={'code':'layer_not_found','message':'Couche introuvable'})
        out = params.get('output') or output_path('clip')
        res = run_processing('native:clip', {'INPUT': l1[0], 'OVERLAY': l2[0], 'OUTPUT': out})
        return ToolResult(ok=True,data={'output': res.get('OUTPUT')})
class Intersection(GeoTool):
    name = "intersection"
    category = "analyze"
    def run(self, params: dict[str, Any]) -> ToolResult:
        input_ = params.get('input') or params.get('layer')
        overlay = params.get('overlay')
        if not input_ or not overlay: return ToolResult(ok=False,error={'code':'missing_param','message':"'input' et 'overlay' requis"})
        l1 = QgsProject.instance().mapLayersByName(str(input_)); l2 = QgsProject.instance().mapLayersByName(str(overlay))
        if not l1 or not l2: return ToolResult(ok=False,error={'code':'layer_not_found','message':'Couche introuvable'})
        out = params.get('output') or output_path('intersection')
        res = run_processing('native:intersection', {'INPUT': l1[0], 'OVERLAY': l2[0], 'OUTPUT': out})
        return ToolResult(ok=True,data={'output': res.get('OUTPUT')})
class Dissolve(GeoTool):
    name = "dissolve"
    category = "analyze"
    def run(self, params: dict[str, Any]) -> ToolResult:
        layer = params.get('layer') or params.get('input')
        if not layer: return ToolResult(ok=False,error={'code':'missing_param','message':"'layer' requis"})
        lyr = QgsProject.instance().mapLayersByName(str(layer))
        if not lyr: return ToolResult(ok=False,error={'code':'layer_not_found','message':f'Couche introuvable: {layer}'})
        out = params.get('output') or output_path('dissolve')
        res = run_processing('native:dissolve', {'INPUT': lyr[0], 'OUTPUT': out})
        return ToolResult(ok=True,data={'output': res.get('OUTPUT')})
class SpatialJoin(GeoTool):
    name = "spatial_join"
    category = "analyze"
    def run(self, params: dict[str, Any]) -> ToolResult:
        input_ = params.get('input')
        join = params.get('join')
        if not input_ or not join: return ToolResult(ok=False,error={'code':'missing_param','message':"'input' et 'join' requis"})
        l1 = QgsProject.instance().mapLayersByName(str(input_)); l2 = QgsProject.instance().mapLayersByName(str(join))
        if not l1 or not l2: return ToolResult(ok=False,error={'code':'layer_not_found','message':'Couche introuvable'})
        out = params.get('output') or output_path('join')
        res = run_processing('native:joinattributesbylocation', {'INPUT': l1[0], 'JOIN': l2[0], 'PREDICATE': [0], 'METHOD': 1, 'OUTPUT': out})
        return ToolResult(ok=True,data={'output': res.get('OUTPUT')})
class DistanceAnalysis(GeoTool):
    name = "distance_analysis"
    category = "analyze"
    def run(self, params: dict[str, Any]) -> ToolResult:
        from1 = params.get('from') or params.get('input1')
        to1 = params.get('to') or params.get('input2')
        if not from1 or not to1: return ToolResult(ok=False,error={'code':'missing_param','message':"'from' et 'to' requis"})
        l1 = QgsProject.instance().mapLayersByName(str(from1)); l2 = QgsProject.instance().mapLayersByName(str(to1))
        if not l1 or not l2: return ToolResult(ok=False,error={'code':'layer_not_found','message':'Couche introuvable'})
        out = params.get('output') or output_path('distances')
        def _first_field(layer):
            fields = layer.fields()
            return fields[0].name() if fields.count() else ''
        res = run_processing('qgis:distancematrix', {
            'INPUT': l1[0],
            'INPUT_FIELD': _first_field(l1[0]),
            'TARGET': l2[0],
            'TARGET_FIELD': _first_field(l2[0]),
            'MATRIX_TYPE': 0,
            'NEAREST_POINTS': 0,
            'OUTPUT': out,
        })
        return ToolResult(ok=True,data={'output': res.get('OUTPUT')})
