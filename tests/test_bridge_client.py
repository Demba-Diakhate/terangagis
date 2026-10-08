import json
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

from mcp.bridge_client import BridgeClient, BridgeClientError


class _Handler(BaseHTTPRequestHandler):
    def log_message(self, *args):
        return

    def _json(self, status, payload):
        data = json.dumps(payload).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        if self.headers.get("X-Teranga-Token") != "secret":
            self._json(401, {"ok": False, "error": {"code": "unauthorized"}})
            return
        if self.path == "/health":
            self._json(200, {"ok": True, "service": "terangagis-bridge"})
        elif self.path == "/v1/tools":
            self._json(200, {"ok": True, "data": [{"name": "buffer"}]})
        else:
            self._json(404, {"ok": False, "error": {"code": "not_found"}})

    def do_POST(self):
        if self.headers.get("X-Teranga-Token") != "secret":
            self._json(401, {"ok": False, "error": {"code": "unauthorized"}})
            return
        length = int(self.headers.get("Content-Length", 0) or 0)
        body = json.loads(self.rfile.read(length) or b"{}")
        if self.path == "/v1/tools/execute":
            if body.get("tool") == "buffer":
                self._json(200, {"ok": True, "data": {"output": "buf.gpkg"}})
            else:
                self._json(404, {"ok": False, "error": {"code": "tool_not_found"}})
        else:
            self._json(404, {"ok": False, "error": {"code": "not_found"}})


def _serve():
    server = HTTPServer(("127.0.0.1", 0), _Handler)
    t = threading.Thread(target=server.serve_forever, daemon=True)
    t.start()
    return server, f"http://127.0.0.1:{server.server_address[1]}"


def test_bridge_client_health_and_tools():
    server, base = _serve()
    try:
        client = BridgeClient(base, "secret")
        assert client.health()["ok"] is True
        assert client.list_tools()["data"][0]["name"] == "buffer"
    finally:
        server.shutdown()


def test_bridge_client_execute_ok():
    server, base = _serve()
    try:
        client = BridgeClient(base, "secret")
        res = client.execute("buffer", {"layer": "L", "distance": 5})
        assert res["ok"] is True
        assert res["data"]["output"] == "buf.gpkg"
    finally:
        server.shutdown()


def test_bridge_client_unauthorized_returns_payload():
    server, base = _serve()
    try:
        client = BridgeClient(base, "wrong")
        res = client.health()
        assert res["ok"] is False
        assert res["error"]["code"] == "unauthorized"
    finally:
        server.shutdown()


def test_bridge_client_connection_error():
    client = BridgeClient("http://127.0.0.1:1", "secret", timeout=0.5)
    try:
        client.health()
        assert False, "devrait lever BridgeClientError"
    except BridgeClientError:
        pass