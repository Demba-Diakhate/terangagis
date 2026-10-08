from plugin.agent.agent import AgentPlan, AgentStep
from plugin.agent.journal import Journal
from plugin.agent.orchestrator import Orchestrator
from plugin.agent.validation import validate_plan


class _FakeClient:
    def __init__(self, results):
        self.results = results
        self.calls = []

    def execute(self, tool, params):
        self.calls.append((tool, params))
        return self.results[tool]


def _plan(*steps):
    return AgentPlan(steps=[AgentStep(tool=t, params=p) for t, p in steps])


def test_validate_plan_missing_required():
    plan = _plan(("get_layer_info", {}))
    report = validate_plan(plan)
    assert not report.ok
    assert any(i.code == 'missing_param' for i in report.errors)


def test_validate_plan_geographic_warning():
    plan = _plan(("buffer", {"layer": "L", "distance": 100}))
    report = validate_plan(plan, layer_crs={"L": "EPSG:4326"})
    assert report.ok  # warning seulement
    assert any(i.code == 'geographic_crs' for i in report.warnings)


def test_validate_plan_output_collision():
    plan = _plan(("save_layer", {"layer": "L", "path": "/data/L.shp"}))
    report = validate_plan(plan, protected_sources=["/data/L.shp"])
    assert not report.ok
    assert any(i.code == 'output_overwrites_source' for i in report.errors)


def test_validate_plan_distance_positive():
    plan = _plan(("buffer", {"layer": "L", "distance": -5}))
    report = validate_plan(plan)
    assert not report.ok


def test_orchestrator_dry_run_does_not_execute():
    client = _FakeClient({})
    orch = Orchestrator(client)
    plan = _plan(("get_project_info", {}))
    report, exec_report = orch.run(plan, dry_run=True)
    assert report.ok
    assert client.calls == []
    assert exec_report.steps == []


def test_orchestrator_executes_in_order():
    client = _FakeClient({
        "get_project_info": {"ok": True, "data": {}},
        "list_layers": {"ok": True, "data": []},
    })
    orch = Orchestrator(client)
    plan = _plan(("get_project_info", {}), ("list_layers", {}))
    report, exec_report = orch.run(plan)
    assert report.ok and exec_report.ok
    assert [c[0] for c in client.calls] == ["get_project_info", "list_layers"]


def test_orchestrator_stops_on_error():
    client = _FakeClient({
        "buffer": {"ok": False, "error": {"code": "x"}},
        "dissolve": {"ok": True, "data": {}},
    })
    orch = Orchestrator(client)
    plan = _plan(("buffer", {"layer": "L", "distance": 1}), ("dissolve", {"layer": "L"}))
    _, exec_report = orch.run(plan)
    assert exec_report.stopped_on_error
    assert len(exec_report.steps) == 1
    assert client.calls == [("buffer", {"layer": "L", "distance": 1})]


def test_orchestrator_journals_events(tmp_path):
    journal = Journal(str(tmp_path / "j.sqlite"))
    client = _FakeClient({"get_project_info": {"ok": True, "data": {}}})
    orch = Orchestrator(client, journal=journal)
    plan = _plan(("get_project_info", {}))
    orch.run(plan)
    assert journal.count("validation") == 1
    assert journal.count("execution") == 1
    journal.close()