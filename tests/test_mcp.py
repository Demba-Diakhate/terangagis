from mcp.server import MCPServer, _tool_defs


class _FakeClient:
    def __init__(self, response):
        self.response = response
        self.calls = []

    def execute(self, tool, params):
        self.calls.append((tool, params))
        return self.response


def test_initialize():
    srv = MCPServer(client=_FakeClient({}))
    resp = srv.handle({"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}})
    assert resp["result"]["serverInfo"]["name"] == "terangagis"
    assert "tools" in resp["result"]["capabilities"]


def test_tools_list_has_17_tools():
    srv = MCPServer(client=_FakeClient({}))
    resp = srv.handle({"jsonrpc": "2.0", "id": 2, "method": "tools/list"})
    tools = resp["result"]["tools"]
    assert len(tools) == 17
    names = {t["name"] for t in tools}
    assert {"buffer", "clip", "get_project_info", "export_map", "find_senegal_sources"} <= names
    assert len(_tool_defs()) == 17


def test_tools_call_success():
    fake = _FakeClient({"ok": True, "data": {"output": "x.gpkg"}})
    srv = MCPServer(client=fake)
    resp = srv.handle({
        "jsonrpc": "2.0", "id": 3, "method": "tools/call",
        "params": {"name": "buffer", "arguments": {"layer": "L", "distance": 10}},
    })
    assert resp["result"]["isError"] is False
    assert fake.calls == [("buffer", {"layer": "L", "distance": 10})]


def test_tools_call_unknown_tool():
    srv = MCPServer(client=_FakeClient({}))
    resp = srv.handle({
        "jsonrpc": "2.0", "id": 4, "method": "tools/call",
        "params": {"name": "nope", "arguments": {}},
    })
    assert resp["error"]["code"] == -32602


def test_unknown_method():
    srv = MCPServer(client=_FakeClient({}))
    resp = srv.handle({"jsonrpc": "2.0", "id": 5, "method": "bogus"})
    assert resp["error"]["code"] == -32601


def test_notification_returns_none():
    srv = MCPServer(client=_FakeClient({}))
    assert srv.handle({"method": "notifications/initialized"}) is None