from __future__ import annotations
import json
import threading
import time
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any, Callable
from qgis.PyQt.QtCore import QCoreApplication, QObject, QThread, Qt, pyqtSignal, pyqtSlot
from qgis.core import QgsProject, QgsVectorLayer
from plugin.core.errors import TerangaError


class BridgeError(TerangaError):
    pass


class _MainInvoker(QObject):
    """Exécute une fonction PyQGIS sur le thread principal via signal/slot Qt.

    L'objet doit être créé sur le thread principal (celui de QGIS). Un appel
    depuis un thread worker émet un signal connecté en `QueuedConnection` ;
    le slot s'exécute donc sur le thread principal, qui doit faire tourner sa
    boucle d'événements (cas normal dans QGIS).
    """

    _trigger = pyqtSignal()

    def __init__(self) -> None:
        super().__init__()
        self._trigger.connect(self._run, Qt.QueuedConnection)
        self._lock = threading.Lock()
        self._fn: Callable[[], Any] | None = None
        self._result: Any = None
        self._error: Exception | None = None
        self._done: threading.Event | None = None

    def invoke(self, fn: Callable[[], Any]) -> Any:
        app = QCoreApplication.instance()
        if app is None:
            raise RuntimeError("QCoreApplication non initialisé")
        if QThread.currentThread() is self.thread():
            return fn()
        with self._lock:
            self._fn = fn
            self._result = None
            self._error = None
            self._done = threading.Event()
            self._trigger.emit()
            if not self._done.wait(timeout=30.0):
                raise RuntimeError("Timeout invocation sur thread principal")
            if self._error is not None:
                raise self._error
            return self._result

    @pyqtSlot()
    def _run(self) -> None:
        try:
            self._result = self._fn() if self._fn is not None else None
        except Exception as e:  # noqa: BLE001
            self._error = e
        finally:
            if self._done is not None:
                self._done.set()


def _map_units_to_str(mu) -> str:
    try:
        return mu.name
    except Exception:
        return str(mu)


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
            geom_str = ['Point', 'Line', 'Polygon', 'Unknown', 'Null'][gt] if 0 <= gt <= 4 else str(gt)
        else:
            try:
                geom_str = lyr.type().name
            except Exception:
                geom_str = str(lyr.type())
        crs_auth = lyr.crs().authid() if lyr.crs().isValid() else ''
        out.append({
            'name': lyr.name(),
            'id': lyr.id(),
            'type': lyr.type().name if hasattr(lyr.type(), 'name') else str(lyr.type()),
            'geometry_type': geom_str,
            'crs': crs_auth,
            'source': lyr.source(),
            'feature_count': lyr.featureCount(),
            'visible': lyr.isValid(),
        })
    return out


def _get_layer_info_sync(name: str, profile: bool = False) -> dict[str, Any] | None:
    proj = QgsProject.instance()
    layers = proj.mapLayersByName(name)
    if not layers:
        return None
    lyr = layers[0]
    fields = []
    for f in lyr.fields():
        fields.append({'name': f.name(), 'type': f.typeName(), 'length': f.length(), 'precision': f.precision()})
    bbox = lyr.extent()
    crs_auth = lyr.crs().authid() if lyr.crs().isValid() else ''
    geom_str = 'Unknown'
    if isinstance(lyr, QgsVectorLayer):
        gt = lyr.geometryType()
        geom_str = ['Point', 'Line', 'Polygon', 'Unknown', 'Null'][gt] if 0 <= gt <= 4 else str(gt)
    info = {
        'name': lyr.name(),
        'id': lyr.id(),
        'crs': crs_auth,
        'geometry_type': geom_str,
        'feature_count': lyr.featureCount(),
        'fields': fields,
        'extent': {'xmin': bbox.xMinimum(), 'ymin': bbox.yMinimum(), 'xmax': bbox.xMaximum(), 'ymax': bbox.yMaximum()},
        'source': lyr.source(),
    }
    if profile and isinstance(lyr, QgsVectorLayer):
        from plugin.geofunc.qgis_profile import layer_profile
        prof = layer_profile(lyr)
        if prof is not None:
            info['profile'] = prof
    return info


def _get_selected_sync() -> list[dict[str, Any]]:
    proj = QgsProject.instance()
    res: list[dict[str, Any]] = []
    for lyr in proj.mapLayers().values():
        if isinstance(lyr, QgsVectorLayer) and lyr.selectedFeatureCount() > 0:
            res.append({'layer': lyr.name(), 'selected_count': lyr.selectedFeatureCount()})
    return res


def _list_tools_sync() -> list[dict[str, Any]]:
    from plugin.geofunc.catalog import get_registry
    registry = get_registry()
    out: list[dict[str, Any]] = []
    for name in registry.list():
        cls = registry.get(name)
        out.append({
            'name': name,
            'description': getattr(cls, 'description', ''),
            'category': getattr(cls, 'category', ''),
        })
    return out


def _artifact_meta(path: str) -> dict[str, Any]:
    """Métadonnées d'une couche produite (vide si non vecteur / illisible)."""
    try:
        lyr = QgsVectorLayer(str(path), 'teranga_meta', 'ogr')
        if not lyr.isValid():
            return {}
        gt = lyr.geometryType()
        geom = ['Point', 'Line', 'Polygon', 'Unknown', 'Null'][gt] if 0 <= gt <= 4 else 'Unknown'
        return {
            'crs': lyr.crs().authid() if lyr.crs().isValid() else '',
            'geometry_type': geom,
            'feature_count': lyr.featureCount(),
        }
    except Exception:  # noqa: BLE001
        return {}


def _execute_tool_sync(tool: str, params: dict[str, Any], store: Any = None) -> dict[str, Any]:
    """Exécute un outil en résolvant les entrées/sorties par nom (S11).

    - les paramètres de couche (`layer`, `input`, `overlay`, `join`, `from`, `to`)
      sont résolus via les artefacts de session puis le projet ;
    - un `output`/`path` fourni comme nom logique est matérialisé en chemin horodaté ;
    - la sortie produite est enregistrée comme artefact et ajoutée au projet.
    """
    from plugin.geofunc.artifacts import logical_name_for_path, looks_like_path
    from plugin.geofunc.catalog import get_registry
    from plugin.geofunc.layer_resolver import (
        LAYER_PARAM_KEYS,
        add_artifact_to_project,
        ensure_layer_in_project,
    )
    from plugin.geofunc.paths import output_path

    registry = get_registry()
    cls = registry.get(tool)
    if cls is None:
        raise BridgeError('tool_not_found', f'Outil introuvable : {tool}')

    call_params = dict(params or {})

    for key in LAYER_PARAM_KEYS:
        value = call_params.get(key)
        if isinstance(value, str) and value:
            try:
                call_params[key] = ensure_layer_in_project(value, store)
            except KeyError:
                pass

    output_names: dict[str, str] = {}
    for key in ('output', 'path'):
        value = call_params.get(key)
        if isinstance(value, str) and value and not looks_like_path(value):
            output_names[key] = value
            call_params[key] = output_path(value)

    payload = cls().run(call_params).to_dict()

    if tool == 'get_layer_info' and payload.get('ok') and payload.get('data'):
        data = payload['data']
        if data.get('profile'):
            try:
                from plugin.agent.recommend import recommend
                data['recommendations'] = recommend(data['profile'])
            except Exception:  # noqa: BLE001
                pass

    if store is not None and payload.get('ok') and payload.get('data'):
        data = payload['data']
        produced = data.get('output') or data.get('path')
        if produced:
            requested = output_names.get('output') or output_names.get('path')
            logical = requested or logical_name_for_path(produced)
            artifact = store.register(logical, produced, tool=tool, **_artifact_meta(produced))
            data.setdefault('artifact', artifact.name)
            add_artifact_to_project(artifact)
    return payload


class _BridgeRequestHandler(BaseHTTPRequestHandler):
    server: "_BridgeServer"

    def log_message(self, fmt: str, *args: Any) -> None:
        return

    def _send_json(self, status: int, payload: dict[str, Any]) -> None:
        data = json.dumps(payload, ensure_ascii=False).encode('utf-8')
        self.send_response(status)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Content-Length', str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def _check_auth(self) -> bool:
        token = self.headers.get('X-Teranga-Token', '')
        return token == self.server.access_token

    def _require_auth(self) -> bool:
        if self._check_auth():
            return True
        self._send_json(401, BridgeError('unauthorized', 'Jeton manquant ou invalide').to_dict())
        return False

    def do_GET(self) -> None:
        if not self._require_auth():
            return
        path, _, query = self.path.partition('?')
        if path == '/health':
            self._send_json(200, {'ok': True, 'service': 'terangagis-bridge'})
            return
        if path == '/v1/project':
            self._handle_project()
            return
        if path == '/v1/layers':
            self._handle_layers()
            return
        if path.startswith('/v1/layers/') and path.endswith('/info'):
            name = path[len('/v1/layers/'):-len('/info')]
            if name.startswith('/'):
                name = name[1:]
            profile = 'profile=1' in query or 'profile=true' in query
            self._handle_layer_info(name, profile)
            return
        if path == '/v1/layers/selected':
            self._handle_selected()
            return
        if path == '/v1/tools':
            self._handle_tools_list()
            return
        if path == '/v1/artifacts':
            self._handle_artifacts()
            return
        if path == '/v1/layers/match' or self.path == '/v1/layers/match':
            self._handle_layers_match()
            return
        self._send_json(404, BridgeError('not_found', f'Route introuvable : {self.path}').to_dict())

    def do_POST(self) -> None:
        if not self._require_auth():
            return
        if self.path == '/v1/tools/execute':
            self._handle_tool_execute()
            return
        self._send_json(404, BridgeError('not_found', f'Route introuvable : {self.path}').to_dict())

    def _handle_project(self) -> None:
        try:
            res = self.server.invoker.invoke(_get_project_info_sync)
            self._send_json(200, {'ok': True, 'data': res})
        except Exception as e:
            self._send_json(500, BridgeError('internal', str(e)).to_dict())

    def _handle_layers(self) -> None:
        try:
            res = self.server.invoker.invoke(_get_layers_list_sync)
            self._send_json(200, {'ok': True, 'data': res})
        except Exception as e:
            self._send_json(500, BridgeError('internal', str(e)).to_dict())

    def _handle_layers_match(self) -> None:
        try:
            length = int(self.headers.get('Content-Length', 0) or 0)
            raw = self.rfile.read(length) if length else b'{}'
            payload = json.loads(raw.decode('utf-8') or '{}')
        except Exception as e:
            self._send_json(400, BridgeError('bad_request', f'Corps JSON invalide : {e}').to_dict())
            return
        instruction = payload.get('instruction') or ''
        try:
            from plugin.geofunc.layer_resolver import resolve_best
            res = self.server.invoker.invoke(lambda: resolve_best(str(instruction)))
            self._send_json(200, {'ok': True, 'data': res})
        except Exception as e:
            self._send_json(500, BridgeError('internal', str(e)).to_dict())

        try:
            length = int(self.headers.get('Content-Length', 0) or 0)
            raw = self.rfile.read(length) if length else b'{}'
            payload = json.loads(raw.decode('utf-8') or '{}')
        except Exception as e:
            self._send_json(400, BridgeError('bad_request', f'Corps JSON invalide : {e}').to_dict())
            return
        instruction = payload.get('instruction') or ''
        try:
            from plugin.geofunc.layer_resolver import resolve_best
            res = self.server.invoker.invoke(lambda: resolve_best(str(instruction)))
            self._send_json(200, {'ok': True, 'data': res})
        except Exception as e:
            self._send_json(500, BridgeError('internal', str(e)).to_dict())

    def _handle_layer_info(self, name: str, profile: bool = False) -> None:
        try:
            res = self.server.invoker.invoke(lambda: _get_layer_info_sync(name, profile))
            if res is None:
                self._send_json(404, BridgeError('layer_not_found', f'Couche introuvable : {name}').to_dict())
                return
            if profile and res.get('profile'):
                try:
                    from plugin.agent.recommend import recommend
                    res['recommendations'] = recommend(res['profile'])
                except Exception:  # noqa: BLE001
                    pass
            self._send_json(200, {'ok': True, 'data': res})
        except Exception as e:
            self._send_json(500, BridgeError('internal', str(e)).to_dict())

    def _handle_selected(self) -> None:
        try:
            res = self.server.invoker.invoke(_get_selected_sync)
            self._send_json(200, {'ok': True, 'data': res})
        except Exception as e:
            self._send_json(500, BridgeError('internal', str(e)).to_dict())

    def _handle_tools_list(self) -> None:
        try:
            res = self.server.invoker.invoke(_list_tools_sync)
            self._send_json(200, {'ok': True, 'data': res})
        except Exception as e:
            self._send_json(500, BridgeError('internal', str(e)).to_dict())

    def _handle_artifacts(self) -> None:
        try:
            self._send_json(200, {'ok': True, 'data': self.server.artifacts.list()})
        except Exception as e:
            self._send_json(500, BridgeError('internal', str(e)).to_dict())

    def _handle_tool_execute(self) -> None:
        try:
            length = int(self.headers.get('Content-Length', 0) or 0)
            raw = self.rfile.read(length) if length else b'{}'
            payload = json.loads(raw.decode('utf-8') or '{}')
        except Exception as e:
            self._send_json(400, BridgeError('bad_request', f'Corps JSON invalide : {e}').to_dict())
            return
        tool = payload.get('tool')
        params = payload.get('params') or {}
        if not tool:
            self._send_json(400, BridgeError('missing_param', "Champ 'tool' requis").to_dict())
            return
        try:
            res = self.server.invoker.invoke(lambda: _execute_tool_sync(tool, params, self.server.artifacts))
        except BridgeError as e:
            self._send_json(404, e.to_dict())
            return
        except Exception as e:  # noqa: BLE001
            self._send_json(500, BridgeError('internal', str(e)).to_dict())
            return
        status = 200 if res.get('ok') else 400
        self._send_json(status, res)


class _BridgeServer(ThreadingHTTPServer):
    def __init__(self, addr, handler, access_token: str, invoker: _MainInvoker):
        super().__init__(addr, handler)
        self.access_token = access_token
        self.invoker = invoker
        from plugin.geofunc.artifacts import ArtifactStore
        self.artifacts = ArtifactStore()


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

        class Handler(_BridgeRequestHandler):
            pass

        self._httpd = _BridgeServer(('127.0.0.1', 0), Handler, self._access_token, self._invoker)
        Handler.server = self._httpd  # type: ignore[attr-defined]
        self._port = self._httpd.server_address[1]
        self._thread = threading.Thread(target=self._httpd.serve_forever, daemon=True)
        self._thread.start()
        return {'base_url': self.base_url, 'token': self.access_token, 'port': self._port}

    def stop(self) -> None:
        if self._httpd is not None:
            self._httpd.shutdown()
            self._httpd.server_close()
            self._httpd = None
        if self._thread is not None:
            self._thread.join(timeout=1.0)
            self._thread = None

    def call_on_main(self, fn: Callable[[], Any]) -> Any:
        return self._invoker.invoke(fn)
