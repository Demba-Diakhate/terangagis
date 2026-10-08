import pytest

from plugin.agent.agent import AgentPlan, AgentStep
from plugin.agent.validation import validate_plan


def test_validation_empty_plan_is_error():
    report = validate_plan(AgentPlan(steps=[]))
    assert not report.ok
    assert report.errors[0].code == 'empty_plan'


def test_validation_unknown_tool_is_error():
    report = validate_plan(AgentPlan(steps=[AgentStep('nope', {})]))
    assert not report.ok
    assert any(i.code == 'unknown_tool' for i in report.errors)


def test_validation_missing_required_param():
    report = validate_plan(AgentPlan(steps=[AgentStep('buffer', {'distance': 100})]))
    assert not report.ok
    assert any(i.code == 'missing_param' for i in report.errors)


@pytest.mark.parametrize('distance', [0, -5, 'abc', None])
def test_validation_bad_or_invalid_distance(distance):
    report = validate_plan(AgentPlan(steps=[AgentStep('buffer', {'layer': 'L', 'distance': distance})]))
    assert not report.ok
    assert any(i.code in ('bad_distance', 'invalid_distance') for i in report.errors)


def test_validation_output_overwrites_source_rt6():
    report = validate_plan(
        AgentPlan(steps=[AgentStep('buffer', {'layer': 'L', 'distance': 10, 'output': 'C:/data/L.gpkg'})]),
        protected_sources=['c:/data/l.gpkg'],
    )
    assert not report.ok
    assert any(i.code == 'output_overwrites_source' for i in report.errors)


def test_validation_geographic_crs_warns_not_errors():
    report = validate_plan(
        AgentPlan(steps=[AgentStep('buffer', {'layer': 'L', 'distance': 10})]),
        layer_crs={'L': 'EPSG:4326'},
    )
    assert report.ok
    assert any(i.code == 'geographic_crs' for i in report.warnings)