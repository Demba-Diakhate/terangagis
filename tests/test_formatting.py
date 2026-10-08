from plugin.agent.agent import AgentPlan, AgentStep
from plugin.agent.validation import ValidationIssue, ValidationReport
from plugin.ui.formatting import format_execution, format_plan, format_validation


class _Step:
    def __init__(self, tool, ok, result=None):
        self.tool = tool
        self.ok = ok
        self.result = result


class _Exec:
    def __init__(self, steps, stopped_on_error=False):
        self.steps = steps
        self.stopped_on_error = stopped_on_error


def test_format_plan_lists_steps():
    plan = AgentPlan(steps=[AgentStep(tool='buffer', params={'layer': 'L', 'distance': 10})],
                     assistant_text='Je crée un tampon.')
    text = format_plan(plan)
    assert 'tampon' in text
    assert 'buffer' in text
    assert 'distance=10' in text


def test_format_plan_empty():
    assert format_plan(AgentPlan(steps=[])) == "Aucune étape."


def test_format_validation_ok_and_errors():
    assert format_validation(ValidationReport()) == "Validation : OK."
    report = ValidationReport(issues=[ValidationIssue('error', 'x', 'Paramètre manquant')])
    assert 'ERREUR' in format_validation(report)


def test_format_execution_mixed():
    report = _Exec(steps=[
        _Step('get_project_info', True, {'ok': True, 'data': {'crs': 'EPSG:4326'}}),
        _Step('buffer', False, {'ok': False, 'error': {'message': 'boom'}}),
    ])
    text = format_execution(report)
    assert 'get_project_info : OK' in text
    assert 'buffer : ÉCHEC' in text
    assert 'boom' in text


def test_format_execution_stopped():
    report = _Exec(steps=[_Step('buffer', False, {'error': {'message': 'x'}})], stopped_on_error=True)
    assert 'interrompue' in format_execution(report)