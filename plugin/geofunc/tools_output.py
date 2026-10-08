from __future__ import annotations
from typing import Any
from qgis.core import QgsProject, QgsVectorLayer, QgsLayoutExporter, QgsPrintLayout, QgsProject
from qgis.PyQt.QtCore import QSize
from .tool_base import GeoTool, ToolResult
import os, time
def _out_path(name: str, ext: str) -> str:
    ts = time.strftime("%Y%m%d_%H%M%S")
    return os.path.join(os.path.expanduser('~'), 'Documents', f"{name}_{ts}.{ext}")
class SaveLayer(GeoTool):
    name = "save_layer"
    def run(self, params: dict[str, Any]) -> ToolResult:
        layer = params.get('layer') or params.get('input')
        path = params.get('path') or params.get('output')
        fmt = params.get('format') or 'GPKG'
        if not layer or not path: return ToolResult(ok=False,error={'code':'missing_param','message':"'layer' et 'path' requis"})
        lyr = QgsProject.instance().mapLayersByName(str(layer))
        if not lyr: return ToolResult(ok=False,error={'code':'layer_not_found','message':f'Couche introuvable: {layer}'})
        l = lyr[0]
        if not isinstance(l, QgsVectorLayer): return ToolResult(ok=False,error={'code':'unsupported','message':'Sauvegarde uniquement vecteur'})
        writer = QgsVectorFileWriter.writeAsVectorFormatV3(l, path, QgsProject.instance().transformContext(), QgsVectorFileWriter.SaveVectorOptions())
        if writer[0] != QgsVectorFileWriter.NoError:
            return ToolResult(ok=False,error={'code':'write_error','message':str(writer)})
        return ToolResult(ok=True,data={'path': path})
class ExportMapPNG(GeoTool):
    name = "export_map"
    def run(self, params: dict[str, Any]) -> ToolResult:
        out = params.get('output') or _out_path('map', 'png')
        width = int(params.get('width') or 1920); height = int(params.get('height') or 1080)
        dpi = int(params.get('dpi') or 96)
        from qgis.utils import iface
        if iface is None:
            return ToolResult(ok=False,error={'code':'no_iface','message':'iface non disponible (QGIS GUI requis ou à simuler)'})
        try:
            img = iface.mapCanvas().grab(QSize(width,height))
            img.save(out)
            return ToolResult(ok=True,data={'output': out, 'width': width, 'height': height})
        except Exception as e:
            return ToolResult(ok=False,error={'code':'export_failed','message':str(e)})
