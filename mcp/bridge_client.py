"""Client HTTP du bridge QGIS (auth par jeton de session)."""
from __future__ import annotations
import json
from typing import Any, Dict
from urllib import request as _request
from urllib.error import HTTPError, URLError


class BridgeClientError(Exception):
    pass


class BridgeClient:
    def __init__(self, base_url: str, token: str, timeout: float = 30.0) -> None:
        self.base_url = base_url.rstrip('/')
        self.token = token
        self.timeout = timeout

    def _request(self, method: str, path: str, body: dict | None = None) -> Dict[str, Any]:
        url = f'{self.base_url}{path}'
        data = None
        headers = {'X-Teranga-Token': self.token}
        if body is not None:
            data = json.dumps(body).encode('utf-8')
            headers['Content-Type'] = 'application/json'
        req = _request.Request(url, data=data, headers=headers, method=method)
        try:
            with _request.urlopen(req, timeout=self.timeout) as resp:
                return json.loads(resp.read().decode('utf-8'))
        except HTTPError as e:
            try:
                return json.loads(e.read().decode('utf-8'))
            except Exception:
                raise BridgeClientError(f'HTTP {e.code} sur {path}') from e
        except URLError as e:
            raise BridgeClientError(f'Connexion au bridge impossible : {e}') from e

    def get(self, path: str) -> Dict[str, Any]:
        return self._request('GET', path)

    def post(self, path: str, body: dict) -> Dict[str, Any]:
        return self._request('POST', path, body)

    def health(self) -> Dict[str, Any]:
        return self.get('/health')

    def list_tools(self) -> Dict[str, Any]:
        return self.get('/v1/tools')

    def execute(self, tool: str, params: dict | None = None) -> Dict[str, Any]:
        return self.post('/v1/tools/execute', {'tool': tool, 'params': params or {}})