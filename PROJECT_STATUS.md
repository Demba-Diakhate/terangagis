# PROJECT_STATUS.md — Tableau de bord TerangaGIS

> **Source de vérité de l'avancement.** Toute session de travail commence par la lecture de ce fichier et se termine par sa mise à jour. Règles : `AGENTS.md`.

**Dernière mise à jour :** 2026-10-08

| Champ | Valeur |
|---|---|
| **Sprint courant** | S00 — Préparation |
| **Statut du sprint** | EN COURS |
| **Tâche en cours** | S00-T5 : squelette du plugin QGIS |
| **Prochaine action** | Installer QGIS 3.44 LTR, puis créer le squelette du plugin |
| **Bloqueurs** | QGIS non installé sur la machine de développement |
| **Sprints terminés** | aucun |

---

## Kanban des sprints

| Sprint | Intitulé | Statut | DoD vérifiée le | Notes |
|---|---|---|---|---|
| S00 | Préparation | **EN COURS** | — | CDC V2 + suivi agile faits ; git/plugin/tests à faire |
| S01 | Contrôle QGIS (bridge HTTP + inspection) | À FAIRE | — | — |
| S02 | Outils SIG (16 outils, Processing-first) | À FAIRE | — | — |
| S03 | Serveur MCP | À FAIRE | — | — |
| S04 | Agent langage naturel | À FAIRE | — | LLM : OpenRouter + Gemini free tier |
| S05 | Planification multi-étapes | À FAIRE | — | — |
| S06 | Interface QGIS (panneau chat) | À FAIRE | — | — |
| S07 | Sécurité et traçabilité | À FAIRE | — | — |
| S08 | Workflows métier (3 démos) | À FAIRE | — | — |
| S09 | Tests et qualité (corpus golden, CI) | À FAIRE | — | — |
| S10 | Release MVP | À FAIRE | — | — |

Légende : `À FAIRE` | `EN COURS` | `FAIT` | `BLOQUÉ`

---

## Détail du sprint courant — S00 Préparation

**Objectif :** environnement et architecture.
**DoD :** dépôt fonctionnel ; QGIS local ; plugin minimal chargé ; premier test Python vert ; README initial ; suivi agile en place.

| ID | Tâche | Statut | Notes |
|---|---|---|---|
| S00-T1 | Cahier des charges combiné V2.0 | FAIT | `../TerangaGIS_Cahier_des_charges_Combine_V2.md` |
| S00-T2 | Système de suivi agile (`AGENTS.md`, `PROJECT_STATUS.md`) | FAIT | — |
| S00-T3 | Créer le dépôt Git + arborescence | À FAIRE | Dans `terangagis/` |
| S00-T4 | Installer QGIS 3.44 LTR | À FAIRE | À télécharger sur qgis.org |
| S00-T5 | Squelette plugin QGIS minimal (chargé dans QGIS) | À FAIRE | `metadata.txt`, panneau vide |
| S00-T6 | Environnement de test + premier test pytest vert | À FAIRE | `qgis.testing` headless |
| S00-T7 | Configuration : `.env.example`, conventions, README initial | À FAIRE | Clés : `OPENROUTER_API_KEY`, `GEMINI_API_KEY` |
| S00-T8 | Documentation architecture | À FAIRE | `docs/architecture.md` |

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
