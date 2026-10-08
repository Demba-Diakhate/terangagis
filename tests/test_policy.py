from plugin.agent.agent import AgentPlan, AgentStep
from plugin.agent.policy import requires_confirmation, risky_steps


def _plan(*tools):
    return AgentPlan(steps=[AgentStep(tool=t, params={}) for t in tools])


def test_read_only_no_confirmation():
    assert requires_confirmation(_plan('get_project_info', 'list_layers')) is False
    assert risky_steps(_plan('get_layer_info')) == []


def test_write_requires_confirmation():
    assert requires_confirmation(_plan('buffer')) is True
    assert requires_confirmation(_plan('get_project_info', 'save_layer')) is True


def test_risky_steps_filters_read_only():
    plan = _plan('list_layers', 'buffer', 'dissolve')
    names = [s.tool for s in risky_steps(plan)]
    assert names == ['buffer', 'dissolve']


def test_empty_plan_no_confirmation():
    assert requires_confirmation(AgentPlan(steps=[])) is False