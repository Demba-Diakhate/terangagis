"""Outils de lecture (S02-T2)."""
from __future__ import annotations
from typing import Any
from qgis.core import QgsProject, QgsVectorLayer
from .tool_base import GeoTool, ToolResult
def _map_units(mu):
    try: return mu.name
    except Exception: return str(mu)
class GetProjectInfo(GeoTool):
    name = "get_project_info"
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
