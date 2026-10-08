import os

import pytest

from plugin.workflows import definitions
from plugin.workflows.definitions import (
    WORKFLOWS,
    build_plan,
    get_workflow,
    layer_name_from_path,
    list_workflows,
)


def test_three_workflows_registered():
    keys = [w.key for w in WORKFLOWS]
    assert keys == ['road_accessibility', 'gps_cleanup', 'health_accessibility']


def test_list_workflows_has_metadata():
    rows = list_workflows()
    assert len(rows) == 3
    assert all(r['title'] and r['instruction'] for r in rows)


def test_road_accessibility_plan_chain():
    plan = build_plan('road_accessibility', {'routes': 'R', 'villages': 'V'}, '/out')
    tools = [s.tool for s in plan.steps]
    assert tools == ['buffer', 'clip']
    buffer_path = plan.steps[0].params['output']
    assert buffer_path.startswith('/out')
    assert plan.steps[1].params['overlay'] == layer_name_from_path(buffer_path)
    assert plan.steps[1].params['input'] == 'V'


def test_gps_cleanup_plan_chain():
    plan = build_plan('gps_cleanup', {'gps': 'G'}, '/out')
    tools = [s.tool for s in plan.steps]
    assert tools == ['fix_geometries', 'remove_duplicates', 'save_layer']
    fixed = plan.steps[0].params['output']
    assert plan.steps[1].params['layer'] == layer_name_from_path(fixed)
    assert plan.steps[1].params['fields'] == ['id']


def test_health_accessibility_uses_distance_threshold():
    plan = build_plan('health_accessibility', {'villages': 'V', 'sante': 'S'}, '/out')
    tools = [s.tool for s in plan.steps]
    assert tools == ['distance_analysis', 'select_by_attribute']
    assert plan.steps[0].params['from'] == 'V'
    assert plan.steps[0].params['to'] == 'S'
    assert '> 10000' in plan.steps[1].params['expression']


def test_missing_layer_raises():
    with pytest.raises(KeyError):
        get_workflow('road_accessibility').build({'routes': 'R'}, '/out')


def test_unknown_workflow_raises():
    with pytest.raises(KeyError):
        get_workflow('nope')


def test_layer_name_from_path():
    assert layer_name_from_path(os.path.join('a', 'b', 'routes_buffer.gpkg')) == 'routes_buffer'