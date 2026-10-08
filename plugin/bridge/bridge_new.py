from __future__ import annotations
import json
import threading
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any, Callable
from qgis.PyQt.QtCore import QCoreApplication, QEvent, QObject
from qgis.core import QgsProject, QgsVectorLayer
from plugin.core.errors import TerangaError

class BridgeError(TerangaError):
    pass

class _InvokeEvent(QEvent):
    TYPE = QEvent.Type(QEvent.User + 1000)
    def __init__(self, fn: Callable[[], Any], invoker: "_MainInvoker") -> None:
        super().__init__(self.TYPE)
        self.fn = fn
        self.invoker = invoker

class _MainInvoker(QObject):
    def __init__(self) -> None:
        super().__init__()
        self._result: Any = None
        self._error: Exception | None = None
        self._done = threading.Event()
    def customEvent(self, event: QEvent) -> None:  # type: ignore[override]
        if isinstance(event, _InvokeEvent):
            try:
                self._result = event.fn()
            except Exception as e:
                self._error = e
            self._done.set()
    def invoke(self, fn: Callable[[], Any]) -> Any:
        self._result = None; self._error = None; self._done.clear()
        app = QCoreApplication.instance()
        if app is None:
            raise RuntimeError("QCoreApplication non initialisé")
        app.postEvent(self, _InvokeEvent(fn, self))
        if not self._done.wait(timeout=30.0):
            raise RuntimeError("Timeout invocation sur thread principal")
        if self._error is not None: raise self._error
        return self._result

def _map_units_to_str(mu) -> str:
    try: return mu.name
    except Exception: return str(mu)

def _get_project_info_sync() -> dict[str, Any]:
    proj = QgsProject.instance()
    return {
        'project_name': proj.title() or proj.fileName() or '',
        'project_file': proj.absoluteFilePath() or proj.fileName() or '',
        'crs': proj.crs().authid() if proj.crs().isValid() else '',
        'map_units': _map_units_to_str(proj.crs().mapUnits()) if proj.crs().isValid() else '',
    }

def _get_layers_list_sync() -> list[dict[str, Any]]:
    proj = QgsProject.instance()
    layers = list(proj.mapLayers().values())
    out: list[dict[str, Any]] = []
    for lyr in layers:
        geom_str = 'Unknown'
        if isinstance(lyr, QgsVectorLayer):
            gt = lyr.geometryType()
            geom_str = ['Point','Line','Polygon','Unknown','Null'][gt] if 0 <= gt <= 4 else str(gt)
        else:
            try: geom_str = lyr.type().name
            except Exception: geom_str = str(lyr.type())
        crs_auth = lyr.crs().authid() if lyr.crs().isValid() else ''
        out.append({
            'name': lyr.name(), 'id': lyr.id(),
            'type': lyr.type().name if hasattr(lyr.type(),'name') else str(lyr.type()),
            'geometry_type': geom_str, 'crs': crs_auth, 'source': lyr.source(),
            'feature_count': lyr.featureCount(), 'visible': lyr.isValid(),
        })
    return out

def _get_layer_info_sync(name: str) -> dict[str, Any] | None:
    proj = QgsProject.instance()
    layers = proj.mapLayersByName(name)
    if not layers: return None
    lyr = layers[0]
    fields = []
    for f in lyr.fields():
        fields.append({'name': f.name(), 'type': f.typeName(), 'length': f.length(), 'precision': f.precision()})
    bbox = lyr.extent()
    crs_auth = lyr.crs().authid() if lyr.crs().isValid() else ''
    geom_str = 'Unknown'
    if isinstance(lyr, QgsVectorLayer):
        gt = lyr.geometryType()
        geom_str = ['Point','Line','Polygon','Unknown','Null'][gt] if 0 <= gt <= 4 else str(gt)
    return {
        'name': lyr.name(), 'id': lyr.id(), 'crs': crs_auth, 'geometry_type': geom_str,
        'feature_count': lyr.featureCount(), 'fields': fields,
        'extent': {'xmin': bbox.xMinimum(),'ymin': bbox.yMinimum(),'xmax': bbox.xMaximum(),'ymax': bbox.yMaximum()},
        'source': lyr.source(),
    }

def _get_selected_sync() -> list[dict[str, Any]]:
    proj = QgsProject.instance()
    res: list[dict[str, Any]] = []
    for lyr in proj.mapLayers().values():
        if isinstance(lyr, QgsVectorLayer) and lyr.selectedFeatureCount() > 0:
            res.append({'layer': lyr.name(), 'selected_count': lyr.selectedFeatureCount()})
    return res

class _BridgeRequestHandler(BaseHTTPRequestHandler):
    server: "_BridgeServer"
    def log_message(self, fmt: str, *args: Any) -> None: return
    def _send_json(self, status: int, payload: dict[str, Any]) -> None:
        data = json.dumps(payload, ensure_ascii=False).encode('utf-8')
        self.send_response(status)
        self.send_header('Content-Type','application/json; charset=utf-8')
        self.send_header('Content-Length', str(len(data)))
        self.end_headers()
        self.wfile.write(data)
    def _check_auth(self) -> bool:
        token = self.headers.get('X-Teranga-Token','')
        return token == self.server.access_token
    def _require_auth(self) -> bool:
        if self._check_auth(): return True
        self._send_json(401, BridgeError('unauthorized','Jeton manquant ou invalide').to_dict())
        return False
    def do_GET(self) -> None:
        if not self._require_auth(): return
        if self.path == '/health': self._send_json(200, {'ok': True,'service':'terangagis-bridge'}); return
        if self.path == '/v1/project': self._handle_project(); return
        if self.path == '/v1/layers': self._handle_layers(); return
        if self.path.startswith('/v1/layers/') and self.path.endswith('/info'):
            name = self.path[len('/v1/layers/'):-len('/info')]
            if name.startswith('/'): name=name[1:]
            self._handle_layer_info(name); return
        if self.path == '/v1/layers/selected': self._handle_selected(); return
        self._send_json(404, BridgeError('not_found',f'Route introuvable : {self.path}').to_dict())
    def do_POST(self) -> None:
        if not self._require_auth(): return
        self._send_json(501, BridgeError('not_implemented','POST non implémenté').to_dict())
    def _handle_project(self) -> None:
        try:
            res = self.server.invoker.invoke(_get_project_info_sync)
            self._send_json(200,{'ok':True,'data':res})
        except Exception as e:
            self._send_json(500, BridgeError('internal',str(e)).to_dict())
    def _handle_layers(self) -> None:
        try:
            res = self.server.invoker.invoke(_get_layers_list_sync)
            self._send_json(200,{'ok':True,'data':res})
        except Exception as e:
            self._send_json(500, BridgeError('internal',str(e)).to_dict())
    def _handle_layer_info(self, name:str) -> None:
        try:
            res = self.server.invoker.invoke(lambda: _get_layer_info_sync(name))
            if res is None: self._send_json(404,BridgeError('layer_not_found',f'Couche introuvable : {name}').to_dict()); return
            self._send_json(200,{'ok':True,'data':res})
        except Exception as e:
            self._send_json(500,BridgeError('internal',str(e)).to_dict())
    def _handle_selected(self) -> None:
        try:
            res = self.server.invoker.invoke(_get_selected_sync)
            self._send_json(200,{'ok':True,'data':res})
        except Exception as e:
            self._send_json(500,BridgeError('internal',str(e)).to_dict())

class _BridgeServer(ThreadingHTTPServer):
    def __init__(self, addr, handler, access_token: str, invoker: '_MainInvoker'):
        super().__init__(addr, handler)
        self.access_token = access_token
        self.invoker = invoker

class BridgeServer:
    def __init__(self) -> None:
        self._httpd: _BridgeServer | None = None
        self._thread: threading.Thread | None = None
        self._access_token = uuid.uuid4().hex
        self._invoker = _MainInvoker()
        self._port = 0
    @property
    def base_url(self) -> str:
        return f'http://127.0.0.1:{self._port}' if self._port else ''
    @property
    def access_token(self) -> str:
        return self._access_token
    def start(self) -> dict[str, Any]:
        if self._httpd is not None:
            return {'base_url': self.base_url, 'token': self.access_token, 'port': self._port}
        class Handler(_BridgeRequestHandler): pass
        self._httpd = _BridgeServer(('127.0.0.1',0), Handler, self._access_token, self._invoker)
        Handler.server = self._httpd  # type: ignore[attr-defined]
        self._port = self._httpd.server_address[1]
        self._thread = threading.Thread(target=self._httpd.serve_forever, daemon=True)
        self._thread.start()
        return {'base_url': self.base_url, 'token': self.access_token, 'port': self._port}
    def stop(self) -> None:
        if self._httpd is not None:
            self._httpd.shutdown(); self._httpd.server_close(); self._httpd = None
        if self._thread is not None:
            self._thread.join(timeout=1.0); self._thread = None
    def call_on_main(self, fn: Callable[[], Any]) -> Any:
        return self._invoker.invoke(fn)
