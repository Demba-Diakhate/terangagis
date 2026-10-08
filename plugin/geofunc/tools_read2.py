"""Outils lecture complément (get_layer_info, get_selected_features)."""
from __future__ import annotations
from typing import Any
from qgis.core import QgsProject, QgsVectorLayer
from .tool_base import GeoTool, ToolResult
class GetLayerInfo(GeoTool):
    name = "get_layer_info"
    def run(self, params: dict[str, Any]) -> ToolResult:
        name = params.get('name') or params.get('layer')
        if not name: return ToolResult(ok=False,error={'code':'missing_param','message':"Paramètre 'name' requis"})
        lyr = QgsProject.instance().mapLayersByName(str(name))
        if not lyr: return ToolResult(ok=False,error={'code':'layer_not_found','message':f'Couche introuvable: {name}'})
        lyr0 = lyr[0]
        fields=[]
        for f in lyr0.fields(): fields.append({'name':f.name(),'type':f.typeName()})
        bbox=lyr0.extent()
        geom='Unknown'
        if isinstance(lyr0,QgsVectorLayer):
            gt=lyr0.geometryType(); geom=['Point','Line','Polygon','Unknown','Null'][gt] if 0<=gt<=4 else str(gt)
        return ToolResult(ok=True,data={'name':lyr0.name(),'crs':lyr0.crs().authid() if lyr0.crs().isValid() else '','feature_count':lyr0.featureCount(),'fields':fields,'extent':{'xmin':bbox.xMinimum(),'ymin':bbox.yMinimum(),'xmax':bbox.xMaximum(),'ymax':bbox.yMaximum()},'geometry_type':geom})
class GetSelectedFeatures(GeoTool):
    name = "get_selected_features"
    def run(self, params: dict[str, Any]) -> ToolResult:
        res=[]
        for lyr in QgsProject.instance().mapLayers().values():
            if isinstance(lyr,QgsVectorLayer) and lyr.selectedFeatureCount()>0:
                res.append({'layer':lyr.name(),'selected_count':lyr.selectedFeatureCount()})
        return ToolResult(ok=True,data={'selected':res})
