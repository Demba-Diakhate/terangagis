import json
import os

from common.config import Settings
from plugin.agent.agent import GeoAgent
from plugin.agent.golden import evaluate, load_corpus, score_plan, validate_corpus
from plugin.agent.llm import LLMClient
from plugin.agent.tools_schema import TOOL_NAMES

CORPUS = os.path.join(os.path.dirname(__file__), 'golden', 'corpus.json')


def test_corpus_structure_is_valid():
    cases = load_corpus(CORPUS)
    assert len(cases) >= 30
    assert validate_corpus(cases, TOOL_NAMES) == []


def test_corpus_has_unique_ids():
    cases = load_corpus(CORPUS)
    ids = [c['id'] for c in cases]
    assert len(ids) == len(set(ids))


def test_corpus_covers_three_workflows():
    cases = {c['id']: c['expected_tools'] for c in load_corpus(CORPUS)}
    assert cases['wf_road_accessibility'] == ['buffer', 'clip']
    assert cases['wf_gps_cleanup'] == ['fix_geometries', 'remove_duplicates', 'save_layer']
    assert cases['wf_health_accessibility'] == ['distance_analysis', 'select_by_attribute']


def test_validate_corpus_reports_problems():
    bad = [
        {'id': 'a', 'instruction': '', 'expected_tools': ['buffer']},
        {'id': 'a', 'instruction': 'x', 'expected_tools': []},
        {'id': 'b', 'instruction': 'y', 'expected_tools': ['nope']},
    ]
    errors = validate_corpus(bad, TOOL_NAMES)
    assert any("dupliqué" in e for e in errors)
    assert any("instruction" in e for e in errors)
    assert any("vide" in e for e in errors)
    assert any("inconnu" in e for e in errors)


def test_score_plan_exact_and_partial():
    full = score_plan(['buffer', 'clip'], ['buffer', 'clip'])
    assert full['exact'] and full['precision'] == 1.0 and full['recall'] == 1.0
    partial = score_plan(['buffer', 'clip'], ['buffer'])
    assert not partial['exact'] and partial['missing'] == ['clip']
    extra = score_plan(['buffer'], ['buffer', 'clip'])
    assert extra['extra'] == ['clip'] and extra['precision'] == 0.5


def _fake_transport(corpus):
    def transport(url, headers, body, timeout):
        payload = json.loads(body)
        user = next((m['content'] for m in reversed(payload['messages']) if m['role'] == 'user'), '')
        calls = [{'id': str(i), 'type': 'function', 'function': {'name': n, 'arguments': '{}'}}
                 for i, n in enumerate(corpus.get(user, []))]
        return {'choices': [{'message': {'role': 'assistant', 'content': 'ok', 'tool_calls': calls}}]}
    return transport


def test_evaluate_with_fake_llm_scores_full():
    cases = load_corpus(CORPUS)
    by_instruction = {c['instruction']: c['expected_tools'] for c in cases}
    settings = Settings(provider='openrouter', base_url='https://fake.test/v1',
                        api_key='fake', model='fake', max_retries=1, timeout=5)
    agent = GeoAgent(llm=LLMClient(settings=settings, transport=_fake_transport(by_instruction)))
    report = evaluate(cases, lambda instr, ctx: [s.tool for s in agent.plan(instr).steps])
    assert report['score'] == 1.0
    assert report['passed'] == report['total']