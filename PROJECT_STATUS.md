# PROJECT_STATUS.md — Tableau de bord TerangaGIS

> **Source de vérité de l'avancement.** Toute session de travail commence par la lecture de ce fichier et se termine par sa mise à jour. Règles : `AGENTS.md`.

**Dernière mise à jour :** 2026-10-08

| Champ | Valeur |
|---|---|
| **Sprint courant** | S03 — Serveur MCP |
| **Statut du sprint** | EN COURS |
| **Tâche en cours** | S03-T2 — MCP stdio + bridge client (squelette) |
| **Prochaine action** | Implémenter les outils MCP (exposition des 16 outils SIG) |
| **Bloqueurs** | aucun |
| **Sprints terminés** | S00, S01, S02 |

---

## Kanban des sprints

| Sprint | Intitulé | Statut | DoD vérifiée le | Notes |
|---|---|---|---|---|
| S00 | Préparation | **FAIT** | 2026-10-08 | CDC V2 + suivi agile faits ; git/plugin/tests à faire |
| S01 | Contrôle QGIS (bridge HTTP + inspection) | **FAIT** | 2026-10-08 | — |
| S02 | Outils SIG (16 outils, Processing-first) | **FAIT** | 2026-10-08 | — |
| S03 | Serveur MCP | **EN COURS** | — | Squelette agent + MCP stdio + bridge client |
| S04 | Agent langage naturel | À FAIRE | — | LLM : OpenRouter + Gemini free tier |
| S05 | Planification multi-étapes | À FAIRE | — | — |
| S06 | Interface QGIS (panneau chat) | À FAIRE | — | — |
| S07 | Sécurité et traçabilité | À FAIRE | — | — |
| S08 | Workflows métier (3 démos) | À FAIRE | — | — |
| S09 | Tests et qualité (corpus golden, CI) | À FAIRE | — | — |
| S10 | Release MVP | À FAIRE | — | — |

Légende : `À FAIRE` | `EN COURS` | `FAIT` | `BLOQUÉ`

---

## Détail du sprint courant — S03 Serveur MCP

**Objectif :** exposer les capacités QGIS à l'agent via MCP (stdio) + client du bridge HTTP.
**DoD :** serveur MCP stdio fonctionnel ; bridge client (auth) ; outils MCP pour inspection + exécution ; tests.

| ID | Tâche | Statut | Notes |
|---|---|---|---|
| S03-T1 | Agent + planning (squelette `plugin/agent/agent.py`) | FAIT | `GeoAgent`, `AgentPlan`, `AgentStep` |
| S03-T2 | MCP stdio + bridge client (`mcp/server.py`, `mcp/bridge_client.py`) | EN COURS | squelette + client GET auth |
| S03-T3 | Outils MCP (inspection + exécution des outils SIG) | À FAIRE | — |
| S03-T4 | Tests MCP | À FAIRE | — |

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
