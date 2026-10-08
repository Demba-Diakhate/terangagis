"""Évaluation du corpus golden TerangaGIS (RT2).

Exécution HORS CI (voir AGENTS.md / CDC). Trois modes :

  python scripts/run_golden.py --validate      # vérifie la structure du corpus
  python scripts/run_golden.py --fake          # auto-test de la notation (sans LLM)
  python scripts/run_golden.py                 # évaluation réelle (clé LLM requise)

Options :
  --corpus PATH   chemin du corpus (défaut : tests/golden/corpus.json)
"""
from __future__ import annotations

import argparse
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from plugin.agent.golden import evaluate, load_corpus, validate_corpus  # noqa: E402
from plugin.agent.tools_schema import TOOL_NAMES  # noqa: E402

DEFAULT_CORPUS = os.path.join(ROOT, 'tests', 'golden', 'corpus.json')


def _plan_tools(plan) -> list:
    return [s.tool for s in getattr(plan, 'steps', [])]


def _fake_transport(corpus_by_instruction):
    def transport(url, headers, body, timeout):
        payload = json.loads(body)
        messages = payload.get('messages', [])
        user = ''
        for msg in reversed(messages):
            if msg.get('role') == 'user':
                user = msg.get('content', '')
                break
        expected = corpus_by_instruction.get(user, [])
        tool_calls = [
            {'id': str(i), 'type': 'function',
             'function': {'name': name, 'arguments': '{}'}}
            for i, name in enumerate(expected)
        ]
        return {'choices': [{'message': {'role': 'assistant', 'content': 'ok', 'tool_calls': tool_calls}}]}
    return transport


def main() -> int:
    parser = argparse.ArgumentParser(description='Évaluation du corpus golden TerangaGIS')
    parser.add_argument('--validate', action='store_true', help='valider seulement la structure')
    parser.add_argument('--fake', action='store_true', help='auto-test sans LLM')
    parser.add_argument('--corpus', default=DEFAULT_CORPUS)
    args = parser.parse_args()

    cases = load_corpus(args.corpus)
    print(f"Corpus : {args.corpus} ({len(cases)} cas)")

    errors = validate_corpus(cases, TOOL_NAMES)
    if errors:
        print(f"Structure invalide ({len(errors)} erreur(s)) :")
        for err in errors:
            print(f"  - {err}")
        return 1
    print("Structure valide.")

    if args.validate and not args.fake:
        return 0

    if args.fake:
        by_instruction = {c['instruction']: c['expected_tools'] for c in cases}
        from common.config import Settings
        from plugin.agent.agent import GeoAgent
        from plugin.agent.llm import LLMClient
        settings = Settings(provider='openrouter', base_url='https://fake.test/v1',
                            api_key='fake', model='fake', max_retries=1, timeout=5)
        llm = LLMClient(settings=settings, transport=_fake_transport(by_instruction))
        agent = GeoAgent(llm=llm)
    else:
        from plugin.agent.agent import GeoAgent
        agent = GeoAgent()

    report = evaluate(cases, lambda instr, ctx: _plan_tools(agent.plan(instr, context=ctx)))

    for row in report['results']:
        if row.get('ok'):
            print(f"  PASS {row['id']}")
        elif 'error' in row:
            print(f"  FAIL {row['id']} — erreur: {row['error']}")
        else:
            print(f"  FAIL {row['id']} — attendu={row['expected']} obtenu={row['actual']}")

    print(f"\nScore : {report['passed']}/{report['total']} ({report['score']:.0%})")
    return 0 if report['score'] == 1.0 else 1


if __name__ == '__main__':
    raise SystemExit(main())