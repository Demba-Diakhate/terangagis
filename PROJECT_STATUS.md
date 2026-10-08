# PROJECT_STATUS.md — Tableau de bord TerangaGIS

> **Source de vérité de l'avancement.** Toute session de travail commence par la lecture de ce fichier et se termine par sa mise à jour. Règles : `AGENTS.md`.

**Dernière mise à jour :** 2026-10-08

| Champ | Valeur |
|---|---|
| **Sprint courant** | S05 — Planification multi-étapes |
| **Statut du sprint** | À FAIRE |
| **Tâche en cours** | — |
| **Prochaine action** | Démarrer S05 (orchestration : validation/dry-run RT3, exécution séquentielle, gestion d'erreurs) |
| **Bloqueurs** | Tests LLM live nécessitent une clé API (H1) |
| **Sprints terminés** | S00, S01, S02, S03, S04 |

---

## Kanban des sprints

| Sprint | Intitulé | Statut | DoD vérifiée le | Notes |
|---|---|---|---|---|
| S00 | Préparation | **FAIT** | 2026-10-08 | CDC V2 + suivi agile faits ; git/plugin/tests à faire |
| S01 | Contrôle QGIS (bridge HTTP + inspection) | **FAIT** | 2026-10-08 | — |
| S02 | Outils SIG (16 outils, Processing-first) | **FAIT** | 2026-10-08 | — |
| S03 | Serveur MCP | **FAIT** | 2026-10-08 | MCP stdio + 16 tools + client bridge + correctif marshalling |
| S04 | Agent langage naturel | **FAIT** | 2026-10-08 | LLM OpenAI-compatible + tool calling + planification |
| S05 | Planification multi-étapes | À FAIRE | — | — |
| S06 | Interface QGIS (panneau chat) | À FAIRE | — | — |
| S07 | Sécurité et traçabilité | À FAIRE | — | — |
| S08 | Workflows métier (3 démos) | À FAIRE | — | — |
| S09 | Tests et qualité (corpus golden, CI) | À FAIRE | — | — |
| S10 | Release MVP | À FAIRE | — | — |

Légende : `À FAIRE` | `EN COURS` | `FAIT` | `BLOQUÉ`

---

## Détail du sprint courant — S05 Planification multi-étapes

**Objectif :** orchestrer un plan en plusieurs étapes avec validation et exécution contrôlée.
**DoD :** validation/dry-run (RT3) ; exécution séquentielle via bridge ; gestion d'erreurs structurée ; journal (RT4) ; tests.

| ID | Tâche | Statut | Notes |
|---|---|---|---|
| S05-T1 | Validation/dry-run du plan (params, CRS, sorties) | À FAIRE | RT3, RT6 |
| S05-T2 | Orchestrateur d'exécution séquentielle | À FAIRE | via BridgeClient |
| S05-T3 | Journal SQLite (prompts/réponses LLM, exécutions) | À FAIRE | RT4 |
| S05-T4 | Tests orchestrateur | À FAIRE | — |

### Sprint terminé — S04 Agent langage naturel

**DoD :** abstraction LLM ; tool calling sur le catalogue ; parsing robuste ; tests.

| ID | Tâche | Statut | Notes |
|---|---|---|---|
| S04-T1 | Abstraction LLM (OpenRouter/Gemini, chat + tools) | FAIT | `plugin/agent/llm.py` (urllib, sans dépendance, transport injectable) |
| S04-T2 | Prompt système + schémas d'outils pour tool calling | FAIT | `plugin/agent/prompts.py`, `plugin/agent/tools_schema.py` (16 outils) |
| S04-T3 | Boucle de planification (`GeoAgent.plan`) | FAIT | `plugin/agent/agent.py` (sans exécution) |
| S04-T4 | Tests (LLM factice + parsing) | FAIT | `tests/test_agent_llm.py` (7 tests) |

### Sprint terminé — S03 Serveur MCP

**DoD :** serveur MCP stdio fonctionnel ; bridge client (auth) ; outils MCP pour inspection + exécution ; tests.

| ID | Tâche | Statut | Notes |
|---|---|---|---|
| S03-T1 | Agent + planning (squelette `plugin/agent/agent.py`) | FAIT | `GeoAgent`, `AgentPlan`, `AgentStep` |
| S03-T2 | MCP stdio + bridge client (`mcp/server.py`, `mcp/bridge_client.py`) | FAIT | JSON-RPC, auth, POST `/v1/tools/execute` |
| S03-T3 | Outils MCP (inspection + exécution des outils SIG) | FAIT | 16 tools, `plugin/geofunc/catalog.py` |
| S03-T4 | Tests MCP | FAIT | `tests/test_mcp.py`, `tests/test_bridge_client.py`, `tests/bridge_http_smoke.py` (19+10 checks) |

### Récapitulatif sprints terminés

- **S00 Préparation** (FAIT 2026-10-08) : CDC V2.0, suivi agile, dépôt Git, QGIS 3.44.15, plugin minimal, tests config (7 verts), `docs/architecture.md`.
- **S01 Contrôle QGIS** (FAIT 2026-10-08) : bridge HTTP `127.0.0.1` + token `X-Teranga-Token`, endpoints `/health`, `/v1/project`, `/v1/layers`, `/v1/layers/{name}/info`, `/v1/layers/selected`, marshalling thread principal Qt.
- **S02 Outils SIG** (FAIT 2026-10-08) : `plugin/geofunc/` — lecture (`get_project_info`, `list_layers`, `get_layer_info`, `get_selected_features`), préparation (`reproject_layer`, `fix_geometries`, `remove_duplicates`, `select_by_attribute`), analyse (`buffer`, `clip`, `intersection`, `dissolve`, `spatial_join`, `distance_analysis`), sortie (`save_layer`, `export_map`) ; Processing-first ; tests `test_geofunc_*` verts (9 tests).

---

## Décisions techniques

| Date | Décision | Référence |
|---|---|---|
| 2026-10-08 | Pont QGIS ↔ MCP = serveur HTTP local embarqué dans le plugin | CDC V2, ADR D-01 |
| 2026-10-08 | Cible QGIS : 3.44 LTR, minimum 3.40 ; QGIS 4.x surveillé | CDC V2, ADR D-02 |
| 2026-10-08 | LLM : OpenRouter + Google Gemini free tier, abstraction compatible OpenAI | CDC V2, ADR D-03 |
| 2026-10-08 | Interface et messages en français | CDC V2, ADR D-04 |
| 2026-10-08 | Cahier des charges combiné V2.0 = document de référence unique | — |

---

## Hypothèses et points ouverts

| # | Point | État |
|---|---|---|
| H1 | Quotas exacts OpenRouter/Gemini free tier | À vérifier au Sprint 4 |
| H5 | Modèle LLM précis selon qualité du tool calling | Arbitrage Sprint 4 |

---

## Historique des sessions

| Date | Session | Fichiers modifiés/créés |
|---|---|---|
| 2026-10-08 | Analyse des 2 CDC v1, plan validé, décisions (LLM, architecture, QGIS, langue) | — |
| 2026-10-08 | Rédaction CDC combiné V2.0 ; création du dépôt de suivi (`AGENTS.md`, `PROJECT_STATUS.md`) | `TerangaGIS_Cahier_des_charges_Combine_V2.md`, `terangagis/AGENTS.md`, `terangagis/PROJECT_STATUS.md` |
| 2026-10-08 | Sprints S00–S02 terminés (dépôt, bridge HTTP, 16 outils SIG) ; S03 démarré (agent + MCP squelettes) | `plugin/bridge/bridge.py`, `plugin/geofunc/*`, `plugin/agent/agent.py`, `mcp/server.py`, `mcp/bridge_client.py`, `tests/*` |
| 2026-10-08 | S03 terminé : serveur MCP stdio + 16 tools, correctif marshalling bridge (signal/slot Qt), catalogue d'outils, tests (19 pytest + 10 checks QGIS) ; S04 démarré | `mcp/*`, `plugin/bridge/bridge.py`, `plugin/geofunc/catalog.py`, `plugin/geofunc/paths.py`, `plugin/geofunc/processing_runner.py`, `tests/*` |
| 2026-10-08 | S04 terminé : abstraction LLM OpenAI-compatible (OpenRouter/Gemini), tool calling (16 outils), planification agent, tests (26 pytest) | `plugin/agent/llm.py`, `plugin/agent/prompts.py`, `plugin/agent/tools_schema.py`, `plugin/agent/agent.py`, `tests/test_agent_llm.py` |
