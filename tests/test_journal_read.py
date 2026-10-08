import json
import tempfile
import os

from plugin.agent.agent import AgentPlan, AgentStep
from plugin.agent.journal import Journal


def _journal(tmp_path):
    return Journal(os.path.join(str(tmp_path), 'j.sqlite'))


def test_recent_returns_events_newest_first(tmp_path):
    j = _journal(tmp_path)
    j.record_plan(AgentPlan(steps=[AgentStep('buffer', {'distance': 10})]))
    j.record_execution('buffer', {'distance': 10}, {'ok': True})
    events = j.recent(limit=10)
    assert [e['kind'] for e in events] == ['execution', 'plan']
    j.close()


def test_recent_filters_by_kind(tmp_path):
    j = _journal(tmp_path)
    j.record_plan(AgentPlan(steps=[]))
    j.record_execution('clip', {}, {'ok': True})
    j.record_execution('clip', {}, {'ok': True})
    assert len(j.recent(kind='execution')) == 2
    assert len(j.recent(kind='plan')) == 1
    j.close()


def test_export_writes_json(tmp_path):
    j = _journal(tmp_path)
    j.record_execution('buffer', {'distance': 10}, {'ok': True})
    out = os.path.join(str(tmp_path), 'export.json')
    j.export(out)
    data = json.loads(open(out, encoding='utf-8').read())
    assert data[0]['kind'] == 'execution'
    assert data[0]['payload']['tool'] == 'buffer'
    j.close()