"""Tests d'intégration du socle Sénégal (S25) : outil, schémas, prompt."""
from __future__ import annotations

from mcp.server import TOOL_SCHEMAS
from plugin.agent.prompts import SYSTEM_PROMPT
from plugin.agent.tools_schema import TOOL_NAMES, openai_tools
from plugin.geofunc.tools_senegal import FindSenegalSources


def test_find_sources_without_query_lists_all():
    result = FindSenegalSources().run({})
    assert result.ok
    data = result.data
    assert data['region'] == 'Sénégal'
    assert data['count'] == len(data['sources']) >= 3
    ids = {s['id'] for s in data['sources']}
    assert {'sen_communes', 'sen_routes', 'sen_hydro'} <= ids


def test_find_sources_with_query_filters():
    result = FindSenegalSources().run({'query': 'route'})
    assert result.ok
    assert result.data['query'] == 'route'
    assert result.data['count'] >= 1
    assert all('route' in s['name'].lower() or any('route' in k.lower() for k in s['keywords'])
               for s in result.data['sources'])


def test_find_sources_unknown_query_returns_empty():
    result = FindSenegalSources().run({'query': 'zzz_inconnu'})
    assert result.ok
    assert result.data['count'] == 0
    assert result.data['sources'] == []


def test_source_entries_expose_expected_fields():
    result = FindSenegalSources().run({})
    for source in result.data['sources']:
        assert source['id'] and source['name'] and source['type']
        assert source['suggested_crs'] == 'EPSG:32628'
        assert isinstance(source['keywords'], list)


def test_tool_registered_in_mcp_and_openai_tools():
    assert 'find_senegal_sources' in TOOL_SCHEMAS
    assert 'find_senegal_sources' in TOOL_NAMES
    assert 'query' in TOOL_SCHEMAS['find_senegal_sources']['properties']
    names = {t['function']['name'] for t in openai_tools()}
    assert 'find_senegal_sources' in names


def test_system_prompt_mentions_senegal_context():
    assert 'find_senegal_sources' in SYSTEM_PROMPT
    assert 'Sénégal' in SYSTEM_PROMPT
    assert 'Analyse route/commune' in SYSTEM_PROMPT
    assert 'Proximité hydrographie' in SYSTEM_PROMPT


def test_senegal_gabarits_preserved():
    from plugin.senegal import (
        SEN_WORKFLOWS,
        SEN_WORKFLOWS_EXTRA,
        get_sen_sources_summary,
    )

    keys = [w.name for w in SEN_WORKFLOWS]
    assert 'analyser_route_commune' in keys
    assert 'hydro_proximite' in keys
    assert any(w.name == 'identification_couche_sen' for w in SEN_WORKFLOWS_EXTRA)
    assert 'Sénégal' in get_sen_sources_summary()
