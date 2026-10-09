# PROJECT_STATUS.md — Tableau de bord TerangaGIS

> **Source de vérité de l'avancement.** Toute session de travail commence par la lecture de ce fichier et se termine par sa mise à jour. Règles : `AGENTS.md`.

**Dernière mise à jour :** 2026-10-09

| Champ | Valeur |
|---|---|
| **Sprint courant** | S13 — Mémoire de conversation + reprise contrôlée (V2 Workflow Agent) |
| **Statut du sprint** | **FAIT** |
| **Tâche en cours** | — |
| **Prochaine action** | Démarrer S14 — (à définir selon roadmap CDC §30) |
| **Bloqueurs** | CI Docker (RT8) non exécutée localement (à valider au premier push) ; tests LLM live (clé absente — H1) |
| **Sprints terminés** | S00, S01, S02, S03, S04, S05, S06, S07, S08, S09, S10, S11, S12, S13 |

---

## Kanban des sprints

| Sprint | Intitulé | Statut | DoD vérifiée le | Notes |
|---|---|---|---|---|
| S00 | Préparation | **FAIT** | 2026-10-08 | CDC V2 + suivi agile faits ; git/plugin/tests à faire |
| S01 | Contrôle QGIS (bridge HTTP + inspection) | **FAIT** | 2026-10-08 | — |
| S02 | Outils SIG (16 outils, Processing-first) | **FAIT** | 2026-10-08 | — |
| S03 | Serveur MCP | **FAIT** | 2026-10-08 | MCP stdio + 16 tools + client bridge + correctif marshalling |
| S04 | Agent langage naturel | **FAIT** | 2026-10-08 | LLM OpenAI-compatible + tool calling + planification |
| S05 | Planification multi-étapes | **FAIT** | 2026-10-08 | Dry-run RT3 + orchestrateur + journal SQLite RT4 |
| S06 | Interface QGIS (panneau chat) | **FAIT** | 2026-10-08 | ChatPanel + QThread + confirmation |
| S07 | Sécurité et traçabilité | **FAIT** | 2026-10-08 | Sanitisation RT7 + journal lecture/export |
| S08 | Workflows métier (3 démos) | **FAIT** | 2026-10-08 | 3 workflows + runner + jeux de test documentés |
| S09 | Tests et qualité (corpus golden, CI) | **FAIT** | 2026-10-08 | Corpus 30 cas + CI Docker/GitHub Actions + doc utilisateur |
| S10 | Release MVP | **FAIT** | 2026-10-08 | Packaging + 12 critères vérifiés |

### V2 — Workflow Agent (roadmap CDC §30)

| Sprint | Intitulé | Statut | DoD vérifiée le | Notes |
|---|---|---|---|---|
| S11 | Réutilisation des sorties intermédiaires | **FAIT** | 2026-10-09 | Registre d'artefacts + résolution par nom dans le bridge |
| S12 | Exécution robuste : retries + erreurs | **FAIT** | 2026-10-09 | Classification transient/permanent, `on_error`, backoff, retry de parsing |
| S13 | Mémoire de conversation + reprise | **FAIT** | 2026-10-09 | `Conversation` (session) + `resume` + correction LLM (1 essai) confirmée |

Légende : `À FAIRE` | `EN COURS` | `FAIT` | `BLOQUÉ`

---

## Détail du sprint courant — S13 Mémoire de conversation + reprise contrôlée

**Objectif :** mémoriser la conversation de session (tours + artefacts) pour permettre les
demandes de suivi, et offrir une reprise contrôlée d'une étape échouée via une correction
LLM unique confirmée par l'utilisateur.

**DoD :** historique réinjecté dans la planification (budget borné), artefacts produits
mémorisés, reprise d'exécution à l'étape échouée, correction LLM en **un seul essai** soumise
à confirmation, aucune boucle automatique, tests verts.

| ID | Tâche | Statut | Notes |
|---|---|---|---|
| S13-T1 | Conversation de session (module pur) | FAIT | `plugin/agent/conversation.py` (`Conversation`, `Turn`, budget tours + caractères) |
| S13-T2 | Injection de l'historique dans la planification | FAIT | `plugin/agent/agent.py` (`plan(..., conversation=None)`, `_conversation_messages`) |
| S13-T3 | Reprise d'exécution à l'étape échouée | FAIT | `plugin/agent/orchestrator.py` (`resume(plan, previous_report, plan_override=...)`) |
| S13-T4 | Correction LLM unique d'une étape échouée | FAIT | `plugin/agent/agent.py` (`repair(failed_step, error_message, context)`) |
| S13-T5 | Branchement panneau chat (`_RepairWorker`, confirmation, reprise) | FAIT | `plugin/ui/chat_panel.py` (`_on_plan`, `_on_executed`, `_attempt_repair`, `_on_repaired`, `_repaired_once`) |
| S13-T6 | Tests | FAIT | `tests/test_conversation.py` (7), `tests/test_resume.py` (3), `tests/test_repair.py` (3), `tests/conversation_smoke.py` (4), `tests/recovery_smoke.py` (3) |

**Bilan des tests S13 :** 114 pytest verts ; smokes QGIS : conversation 4/4, recovery 3/3,
chat 4/4, artifacts 11/11, bridge 10/10, tools 16/16, workflows 8/8, e2e 7/7, plugin 6/6 — tous verts.

### Sprint terminé — S12 Exécution robuste : retries + gestion d'erreur fine

**Objectif :** durcir la planification/exécution multi-étapes : classification des
erreurs, politique par étape (`stop`/`continue`), retries limités avec backoff,
reprise de parsing du plan (R3).

**DoD :** erreurs transitoires réessayées (succès possible), erreurs permanentes non
réessayées, poursuite possible après échec, retry de parsing, tests verts.

| ID | Tâche | Statut | Notes |
|---|---|---|---|
| S12-T1 | Classification d'erreurs + backoff (pur) | FAIT | `plugin/agent/retry.py` (`classify_error`, `is_retryable`, `backoff_seconds`) |
| S12-T2 | Orchestrateur : `on_error` par étape, retries + backoff, `ExecutionReport` enrichi | FAIT | `plugin/agent/orchestrator.py` (`attempts`, `error_class`, `failed_index`, `recoverable`) |
| S12-T3 | Retry de parsing du plan (correction LLM, R3) | FAIT | `plugin/agent/agent.py` (`parse_retries`) |
| S12-T4 | Client LLM : `retryable`/`Retry-After`, backoff, `sleep` injectable | FAIT | `plugin/agent/llm.py` (`LLMError.retryable`, `LLMClient(sleep=...)`) |
| S12-T5 | Configuration (`TERANGA_STEP_MAX_RETRIES`, `TERANGA_LLM_BACKOFF`) + branchement plugin | FAIT | `common/config.py`, `.env.example`, `plugin/terangagis_plugin.py`, `plugin/ui/chat_panel.py` |
| S12-T6 | Tests | FAIT | `tests/test_retry.py` (6), `tests/test_orchestrator_retry.py` (7), `tests/test_llm_retry.py` (5) |

**Bilan des tests S12 :** 101 pytest verts ; smokes QGIS : artifacts 11/11, bridge 10/10,
tools 16/16, workflows 8/8, e2e 7/7, plugin 6/6, chat 4/4 — tous verts.

### Sprint terminé — S11 Réutilisation des sorties intermédiaires

**Objectif :** permettre à un plan multi-étapes généré par l'agent d'enchaîner ses
étapes en réutilisant les sorties intermédiaires **par nom**, sans rechargement manuel
de fichier (roadmap CDC §30, V2).

**DoD :** un chaînage `buffer` (sortie nommée) → `clip` (référence par nom) fonctionne
sans intervention ; les couches produites sont ajoutées au projet et exposées ; tests verts.

| ID | Tâche | Statut | Notes |
|---|---|---|---|
| S11-T1 | Registre d'artefacts pur (nom logique → chemin + métadonnées) | FAIT | `plugin/geofunc/artifacts.py` (`ArtifactStore`, `logical_name_for_path`, `looks_like_path`) |
| S11-T2 | Résolution de couche (artefact → projet → chemin) + ajout au projet | FAIT | `plugin/geofunc/layer_resolver.py` (`ensure_layer_in_project`, `add_artifact_to_project`) |
| S11-T3 | Branchement du registre dans le bridge (résolution entrées/sorties, `artifact`, `GET /v1/artifacts`) | FAIT | `plugin/bridge/bridge.py` (`_execute_tool_sync`, `_BridgeServer.artifacts`) |
| S11-T4 | Prompt : nommer les sorties et les référencer dans les étapes suivantes | FAIT | `plugin/agent/prompts.py` |
| S11-T5 | Tests | FAIT | `tests/test_artifacts.py` (7), `tests/artifacts_smoke.py` (11 checks QGIS) |

**Bilan des tests S11 :** 83 pytest verts ; smokes QGIS : artifacts 11/11, bridge 10/10,
tools 16/16, workflows 8/8, e2e 7/7, plugin 6/6, chat 4/4 — tous verts.

### Sprint terminé — S10 Release MVP

**Livrables :** plugin QGIS, serveur MCP, agent, tests, documentation technique et
utilisateur, exemples/workflows, jeux de données de démonstration, scripts
d'installation, paquet installable, rapport de validation.

| ID | Tâche | Statut | Notes |
|---|---|---|---|
| S10-T1 | Plugin relocalisable + paquets embarqués (`common`, `mcp`) | FAIT | `plugin/__init__.py` (alias `plugin`, sys.path) |
| S10-T2 | Packaging installable | FAIT | `scripts/build_plugin.py` → `dist/terangagis-1.0.0.zip` |
| S10-T3 | Script d'installation dev | FAIT | `scripts/install_plugin.ps1` |
| S10-T4 | Métadonnées de release | FAIT | `plugin/metadata.txt` version=1.0.0 |
| S10-T5 | Vérification des 12 critères d'acceptation (§23) | FAIT | tableau ci-dessous |

**Vérification des 12 critères d'acceptation du MVP (§23 du CDC)**

| # | Critère | Vérifié | Preuve |
|---|---|---|---|
| 1 | QGIS peut communiquer avec TerangaGIS | OUI | bridge HTTP local ; `tests/bridge_http_smoke.py` (10/10), `tests/plugin_smoke.py` (6/6) |
| 2 | Le projet et les couches peuvent être inspectés | OUI | `/v1/project`, `/v1/layers`, outils lecture ; `tests/tools_smoke.py` |
| 3 | L'utilisateur peut donner une instruction en langage naturel | OUI | `plugin/ui/chat_panel.py` + `plugin/agent/agent.py` |
| 4 | L'agent peut produire un plan | OUI | `GeoAgent.plan` ; `tests/e2e_agent_smoke.py`, `tests/test_agent_llm.py` |
| 5 | Le plan peut être validé | OUI | `plugin/agent/validation.py` (RT3) ; `tests/test_errors.py`, `tests/test_orchestrator.py` |
| 6 | Au moins quinze outils disponibles | OUI | 16 outils ; `tests/tools_smoke.py` (16/16) |
| 7 | Plusieurs outils peuvent être enchaînés | OUI | `plugin/agent/orchestrator.py`, `plugin/workflows/runner.py` |
| 8 | Les erreurs sont gérées | OUI | `plugin/core/errors.py`, `ToolResult`, `tests/test_errors.py` |
| 9 | Les opérations sensibles demandent confirmation | OUI | `plugin/agent/policy.py` + dialogue QMessageBox |
| 10 | Les résultats sont ajoutés/exportés correctement | OUI | `save_layer`, `export_map` ; runner qui ajoute les sorties |
| 11 | Les actions sont journalisées | OUI | `plugin/agent/journal.py` (SQLite, RT4) ; `tests/test_journal_read.py` |
| 12 | Trois workflows de démonstration sont fonctionnels | OUI | `tests/workflows_smoke.py` (8/8) sur jeux de test documentés |

**Bilan des tests de release :** 76 pytest + packaging_smoke (15 checks) +
smokes QGIS (16 + 10 + 8 + 6 + 4 + 7 checks) — tous verts.

### Sprint terminé — S09 Tests et qualité

**DoD :** tests unitaires/intégration/erreur/sécurité verts ; corpus golden (RT2) ; CI Docker (RT8) ; documentation utilisateur.

| ID | Tâche | Statut | Notes |
|---|---|---|---|
| S09-T1 | Corpus golden (~30 instructions FR → outils attendus) | FAIT | `tests/golden/corpus.json` (30 cas), `plugin/agent/golden.py` |
| S09-T2 | Runner d'évaluation hors CI (RT2) | FAIT | `scripts/run_golden.py` (`--validate`, `--fake`, réel) ; auto-test 30/30 |
| S09-T3 | Tests d'erreur et de sécurité | FAIT | `tests/test_errors.py`, `tests/test_sanitization.py` |
| S09-T4 | CI Docker qgis/qgis + GitHub Actions (RT8) | FAIT | `Dockerfile.ci`, `.github/workflows/ci.yml` |
| S09-T5 | Documentation utilisateur | FAIT | `docs/guide_utilisateur.md`, README actualisé |

### Sprint terminé — S08 Workflows métier (3 démos)

**DoD :** les trois workflows fonctionnent sur des jeux de données de test documentés.

| ID | Tâche | Statut | Notes |
|---|---|---|---|
| S08-T1 | Accessibilité aux routes (buffer 5 km → clip villages) | FAIT | `plugin/workflows/definitions.py` |
| S08-T2 | Nettoyage de données GPS (fix_geometries → remove_duplicates → save_layer) | FAIT | idem |
| S08-T3 | Accessibilité aux postes de santé (distance_analysis → select_by_attribute) | FAIT | seuil 10 km (RT5) |
| S08-T4 | Exécution en chaîne (chargement des sorties intermédiaires) | FAIT | `plugin/workflows/runner.py` |
| S08-T5 | Jeux de données de test documentés + smoke QGIS + tests unitaires | FAIT | `tests/workflows_smoke.py` (8), `tests/test_workflows.py` (8) |

### Sprint terminé — S07 Sécurité et traçabilité

**DoD :** sanitisation des données envoyées au LLM (RT7), journalisation exposée, gestion d'erreurs homogène, tests.

| ID | Tâche | Statut | Notes |
|---|---|---|---|
| S07-T1 | Sanitisation des attributs/aperçus envoyés au LLM (RT7) | FAIT | `plugin/agent/sanitization.py` (troncature, contrôle, secrets) |
| S07-T2 | Exposition du journal (consultation) | FAIT | `Journal.recent()` / `Journal.export()` (RT4) |
| S07-T3 | Branchement sanitisation + journal dans l'agent/plugin | FAIT | `agent.py` sanitise contexte/instruction ; `terangagis_plugin.py` crée le `Journal`, expose le contexte projet |
| S07-T4 | Tests sécurité/traçabilité | FAIT | `test_sanitization` (6), `test_journal_read` (3) |

### Sprint terminé — S06 Interface QGIS (panneau chat)

**DoD :** saisie d'instruction, affichage du plan/résultats, confirmation des opérations risquées, en français.

| ID | Tâche | Statut | Notes |
|---|---|---|---|
| S06-T1 | Panneau chat (widget Qt) dans le dock | FAIT | `plugin/ui/chat_panel.py` |
| S06-T2 | Branchement agent + orchestrateur (QThread) | FAIT | UI non bloquée (R6) |
| S06-T3 | Confirmation des opérations risquées | FAIT | `plugin/agent/policy.py` + QMessageBox |
| S06-T4 | Tests (format/policy + smokes UI) | FAIT | `test_policy`, `test_formatting`, `chat_panel_smoke`, `plugin_smoke` |

### Sprint terminé — S05 Planification multi-étapes

**DoD :** validation/dry-run (RT3) ; exécution séquentielle ; gestion d'erreurs ; journal (RT4) ; tests.

| ID | Tâche | Statut | Notes |
|---|---|---|---|
| S05-T1 | Validation/dry-run du plan | FAIT | `plugin/agent/validation.py` |
| S05-T2 | Orchestrateur d'exécution séquentielle | FAIT | `plugin/agent/orchestrator.py` |
| S05-T3 | Journal SQLite (RT4) | FAIT | `plugin/agent/journal.py` |
| S05-T4 | Tests orchestrateur | FAIT | `tests/test_orchestrator.py` (8) |

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
| 2026-10-08 | Marshalling bridge : signal/slot Qt (`QueuedConnection`) sur un `QObject` du thread principal (remplace `QTimer.singleShot` en thread worker) | `plugin/bridge/bridge.py` |
| 2026-10-08 | `distance_analysis` = `qgis:distancematrix` (fournisseur QGIS ; non `native:` en 3.44), champs d'identité auto | RT1, `plugin/geofunc/tools_analyze.py` |
| 2026-10-08 | L'agent/orchestrateur s'exécute hors thread principal ; le bridge service la boucle Qt du thread principal | R6, `tests/e2e_agent_smoke.py` |
| 2026-10-08 | Sanitisation systématique (RT7) de l'instruction et du contexte projet avant envoi au LLM (troncature 200, motifs de secrets neutralisés) | RT7, `plugin/agent/sanitization.py` |
| 2026-10-08 | Workflows métier = plans d'outils déclaratifs (`Workflow`), exécutés en chaîne par un runner qui recharge chaque sortie dans le projet sous son nom de fichier | S08, `plugin/workflows/` |
| 2026-10-08 | Corpus golden séparé du code plugin (`plugin/agent/golden.py` pur + `tests/golden/corpus.json`), évalué hors CI via `scripts/run_golden.py` | RT2, S09 |
| 2026-10-08 | Plugin rendu **relocalisable** : `plugin/__init__.py` enregistre l'alias `sys.modules['plugin']` et ajoute le dossier du plugin au `sys.path`, permettant d'embarquer `common`/`mcp` et de s'installer sous le nom `terangagis` | S10, `plugin/__init__.py` |
| 2026-10-08 | Release MVP versionnée `1.0.0` ; paquet `dist/terangagis-1.0.0.zip` (dossier `terangagis/` autonome) | S10, `scripts/build_plugin.py`, `plugin/metadata.txt` |
| 2026-10-09 | Réutilisation des sorties intermédiaires : registre d'artefacts **côté bridge** (durée = session), résolution des entrées par nom (artefact → projet → chemin) et ajout des couches produites au projet QGIS ; sortie nommable via `output` (nom logique) | V2/S11, `plugin/geofunc/artifacts.py`, `plugin/geofunc/layer_resolver.py`, `plugin/bridge/bridge.py` |
| 2026-10-09 | Exécution robuste : erreurs classées `transient`/`permanent`/`unknown` ; politique `on_error` (`stop`/`continue`) et retries (backoff exponentiel) **par étape** ; retry de parsing du plan côté agent ; erreurs LLM non-réessables (4xx) vs réessables (429/5xx/timeout) avec `Retry-After` | V2/S12, `plugin/agent/retry.py`, `plugin/agent/orchestrator.py`, `plugin/agent/agent.py`, `plugin/agent/llm.py` |
| 2026-10-09 | Mémoire de conversation **limitée à la session** (aucune persistance) ; reprise d'une étape échouée = **une seule** correction LLM proposée puis confirmée par l'utilisateur (pas de boucle automatique) ; `recoverable` ne concerne que les erreurs `transient`/`unknown` | V2/S13, `plugin/agent/conversation.py`, `plugin/agent/orchestrator.py`, `plugin/agent/agent.py`, `plugin/ui/chat_panel.py` |

---

## Hypothèses et points ouverts

| # | Point | État |
|---|---|---|
| H1 | Quotas exacts OpenRouter/Gemini free tier | À vérifier au Sprint 4 |
| H5 | Modèle LLM précis selon qualité du tool calling | Arbitrage Sprint 4 |
| H6 | CI Docker (RT8) : image `qgis/qgis:release-3_44` à valider au premier push (non exécutable dans l'environnement de dev courant) | Sprint 9 |

---

## Historique des sessions

| Date | Session | Fichiers modifiés/créés |
|---|---|---|
| 2026-10-08 | Analyse des 2 CDC v1, plan validé, décisions (LLM, architecture, QGIS, langue) | — |
| 2026-10-08 | Rédaction CDC combiné V2.0 ; création du dépôt de suivi (`AGENTS.md`, `PROJECT_STATUS.md`) | `TerangaGIS_Cahier_des_charges_Combine_V2.md`, `terangagis/AGENTS.md`, `terangagis/PROJECT_STATUS.md` |
| 2026-10-08 | Sprints S00–S02 terminés (dépôt, bridge HTTP, 16 outils SIG) ; S03 démarré (agent + MCP squelettes) | `plugin/bridge/bridge.py`, `plugin/geofunc/*`, `plugin/agent/agent.py`, `mcp/server.py`, `mcp/bridge_client.py`, `tests/*` |
| 2026-10-08 | S03 terminé : serveur MCP stdio + 16 tools, correctif marshalling bridge (signal/slot Qt), catalogue d'outils, tests (19 pytest + 10 checks QGIS) ; S04 démarré | `mcp/*`, `plugin/bridge/bridge.py`, `plugin/geofunc/catalog.py`, `plugin/geofunc/paths.py`, `plugin/geofunc/processing_runner.py`, `tests/*` |
| 2026-10-08 | S04 terminé : abstraction LLM OpenAI-compatible (OpenRouter/Gemini), tool calling (16 outils), planification agent, tests (26 pytest) | `plugin/agent/llm.py`, `plugin/agent/prompts.py`, `plugin/agent/tools_schema.py`, `plugin/agent/agent.py`, `tests/test_agent_llm.py` |
| 2026-10-08 | S05 terminé : validation/dry-run (RT3), orchestrateur séquentiel, journal SQLite (RT4), tests (35 pytest) ; S06 à démarrer | `plugin/agent/validation.py`, `plugin/agent/orchestrator.py`, `plugin/agent/journal.py`, `tests/test_orchestrator.py` |
| 2026-10-08 | Durcissement : balayage des 16 outils (QGIS), test e2e agent→orchestrateur→bridge, branchement du bridge dans le plugin ; correctifs marshalling (signal/slot Qt), `qgis:distancematrix`, sorties inscriptibles, journal thread-safe | `plugin/bridge/bridge.py`, `plugin/geofunc/*`, `plugin/agent/journal.py`, `plugin/terangagis_plugin.py`, `tests/tools_smoke.py`, `tests/e2e_agent_smoke.py`, `tests/plugin_smoke.py` |
| 2026-10-08 | S06 terminé : interface de dialogue (ChatPanel + QThread + confirmation), formatage FR, politique de confirmation ; tests (44 pytest + smokes UI) | `plugin/ui/chat_panel.py`, `plugin/ui/formatting.py`, `plugin/agent/policy.py`, `plugin/terangagis_plugin.py`, `tests/*` |
| 2026-10-08 | S07 terminé : sanitisation RT7, journal lecture/export, branchement sanitisation + journal dans l'agent/plugin ; tests (53 pytest + smokes QGIS) ; S08 à démarrer | `plugin/agent/sanitization.py`, `plugin/agent/journal.py`, `plugin/agent/agent.py`, `plugin/terangagis_plugin.py`, `tests/test_sanitization.py`, `tests/test_journal_read.py` |
| 2026-10-08 | S08 terminé : 3 workflows métier (routes, nettoyage GPS, postes de santé), runner de chaînage, jeux de test documentés, exemples dans le prompt ; tests (61 pytest + 8 checks workflows) ; S09 à démarrer | `plugin/workflows/*`, `plugin/agent/prompts.py`, `tests/test_workflows.py`, `tests/workflows_smoke.py` |
| 2026-10-08 | S09 terminé : corpus golden (30 cas) + runner hors CI, tests erreur/sécurité, CI Docker qgis/qgis + GitHub Actions, guide utilisateur ; tests (76 pytest + smokes QGIS) ; S10 à démarrer | `tests/golden/corpus.json`, `plugin/agent/golden.py`, `scripts/run_golden.py`, `tests/test_golden_corpus.py`, `tests/test_errors.py`, `Dockerfile.ci`, `.github/workflows/ci.yml`, `docs/guide_utilisateur.md` |
| 2026-10-08 | S10 terminé : plugin relocalisable, packaging `dist/terangagis-1.0.0.zip`, script d'installation, métadonnées 1.0.0, vérification des 12 critères du MVP ; tests (76 pytest + packaging + smokes QGIS) — **Release MVP** | `plugin/__init__.py`, `plugin/metadata.txt`, `scripts/build_plugin.py`, `scripts/install_plugin.ps1`, `tests/packaging_smoke.py`, `.github/workflows/ci.yml`, `README.md`, `docs/guide_utilisateur.md` |
| 2026-10-09 | S11 terminé (V2 démarré) : réutilisation des sorties intermédiaires par nom — registre d'artefacts (bridge), résolution de couche + ajout au projet, `GET /v1/artifacts`, prompt de nommage ; tests (83 pytest + smoke artifacts 11/11) ; S12 à démarrer | `plugin/geofunc/artifacts.py`, `plugin/geofunc/layer_resolver.py`, `plugin/bridge/bridge.py`, `plugin/agent/prompts.py`, `tests/test_artifacts.py`, `tests/artifacts_smoke.py`, `README.md`, `docs/architecture.md` |
| 2026-10-09 | S12 terminé : exécution robuste — classification d'erreurs + backoff, `on_error`/retries par étape, `ExecutionReport` enrichi, retry de parsing du plan, client LLM `retryable`/`Retry-After`, config ; tests (101 pytest + smokes QGIS) ; S13 à démarrer | `plugin/agent/retry.py`, `plugin/agent/orchestrator.py`, `plugin/agent/agent.py`, `plugin/agent/llm.py`, `plugin/agent/journal.py`, `plugin/ui/chat_panel.py`, `plugin/terangagis_plugin.py`, `common/config.py`, `.env.example`, `tests/test_retry.py`, `tests/test_orchestrator_retry.py`, `tests/test_llm_retry.py` |
| 2026-10-09 | S13 terminé : mémoire de conversation de session (`Conversation`) injectée dans la planification, reprise d'exécution (`Orchestrator.resume`) et correction LLM unique (`GeoAgent.repair`) confirmée par l'utilisateur ; tests (114 pytest + smokes conversation 4/4, recovery 3/3) ; S14 à démarrer | `plugin/agent/conversation.py`, `plugin/agent/agent.py`, `plugin/agent/orchestrator.py`, `plugin/ui/chat_panel.py`, `tests/test_conversation.py`, `tests/test_resume.py`, `tests/test_repair.py`, `tests/conversation_smoke.py`, `tests/recovery_smoke.py`, `README.md`, `docs/architecture.md` |
