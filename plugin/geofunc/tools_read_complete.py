from __future__ import annotations
from typing import Any
from qgis.core import QgsProject, QgsVectorLayer
from .tool_base import GeoTool, ToolResult

def _map_units(mu):
    try: return mu.name
    except Exception: return str(mu)

def _truthy(value):
    if isinstance(value, str):
        return value.strip().lower() in ('1', 'true', 'oui', 'yes', 'on')
    return bool(value)

class GetProjectInfo(GeoTool):
    name = "get_project_info"
    category = "read"
    def run(self, params: dict[str, Any]) -> ToolResult:
        proj = QgsProject.instance()
        crs = proj.crs()
        return ToolResult(ok=True, data={
            'project_name': proj.title() or proj.fileName() or '',
            'project_file': proj.absoluteFilePath() or proj.fileName() or '',
            'crs': crs.authid() if crs.isValid() else '',
            'map_units': _map_units(crs.mapUnits()) if crs.isValid() else '',
        })

class ListLayers(GeoTool):
    name = "list_layers"
    category = "read"
    def run(self, params: dict[str, Any]) -> ToolResult:
        proj = QgsProject.instance()
        out=[]
        for lyr in proj.mapLayers().values():
            geom_str='Unknown'
            if isinstance(lyr,QgsVectorLayer):
                gt=lyr.geometryType()
                geom_str=['Point','Line','Polygon','Unknown','Null'][gt] if 0<=gt<=4 else str(gt)
            else:
                try: geom_str=lyr.type().name
                except: geom_str=str(lyr.type())
            crs_auth=lyr.crs().authid() if lyr.crs().isValid() else ''
            out.append({'name':lyr.name(),'id':lyr.id(),'type':str(lyr.type()),'geometry_type':geom_str,'crs':crs_auth,'feature_count':lyr.featureCount()})
        return ToolResult(ok=True,data={'layers':out})

class GetLayerInfo(GeoTool):
    name = "get_layer_info"
    category = "read"
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
        data={'name':lyr0.name(),'crs':lyr0.crs().authid() if lyr0.crs().isValid() else '','feature_count':lyr0.featureCount(),'fields':fields,'extent':{'xmin':bbox.xMinimum(),'ymin':bbox.yMinimum(),'xmax':bbox.xMaximum(),'ymax':bbox.yMaximum()},'geometry_type':geom}
        if _truthy(params.get('profile')) and isinstance(lyr0, QgsVectorLayer):
            from .qgis_profile import layer_profile
            prof = layer_profile(lyr0)
            if prof is not None:
                data['profile'] = prof
        return ToolResult(ok=True, data=data)

class GetSelectedFeatures(GeoTool):
    name = "get_selected_features"
    category = "read"
    def run(self, params: dict[str, Any]) -> ToolResult:
        res=[]
        for lyr in QgsProject.instance().mapLayers().values():
            if isinstance(lyr,QgsVectorLayer) and lyr.selectedFeatureCount()>0:
                res.append({'layer':lyr.name(),'selected_count':lyr.selectedFeatureCount()})
        return ToolResult(ok=True,data={'selected':res})
