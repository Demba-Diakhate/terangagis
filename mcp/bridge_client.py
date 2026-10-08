"""Client HTTP vers bridge QGIS (127.0.0.1:port + token)."""
from __future__ import annotations
import http.client
import json
from typing import Any, Dict
class BridgeClient:
    def __init__(self, host: str, port: int, token: str) -> None:
        self.host = host; self.port = port; self.token = token
    def get(self, path: str) -> Dict[str, Any]:
        conn = http.client.HTTPConnection(self.host, self.port, timeout=5)
        headers = {'X-Teranga-Token': self.token}
        conn.request('GET', path, headers=headers)
        resp = conn.getresponse()
        data = resp.read().decode('utf-8', errors='replace')
        try:
            return json.loads(data)
        except Exception:
            return {'ok': False, 'error': {'code': 'json_error', 'message': data}}
