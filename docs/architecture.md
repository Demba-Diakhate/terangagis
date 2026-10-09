# Architecture TerangaGIS (Sprint 0)

Référence : cahier des charges combiné V2.0 — `../../TerangaGIS_Cahier_des_charges_Combine_V2.md`
(ADR D-01 à D-07, §9 Architecture cible, §21 Règles de robustesse).

## Vue d'ensemble

```text
Utilisateur
    |
    v
Interface de chat dans QGIS (plugin/ + plugin/ui/)
    |                          ^
    v                          | signaux Qt (thread principal)
Agent TerangaGIS (plugin/agent/)
    |
    v (MCP stdio)
Serveur MCP (mcp_server/)
    |
    v (HTTP 127.0.0.1 + jeton, Sprint 1)
Serveur HTTP embarqué (plugin/bridge/)
    |
    v
PyQGIS / QGIS Processing (plugin/geofunc/)
    |
    v
Données SIG + journal SQLite (plugin/core/)
```

## Modules et responsabilités

| Emplacement | Rôle | Sprint |
|---|---|---|
| `plugin/terangagis_plugin.py` | Point d'entrée QGIS, dock panel | S00 (squelette) |
| `plugin/ui/` | Panneau chat, affichage du plan, Exécuter/Annuler | S06 |
| `plugin/agent/` | Boucle agent : compréhension, planification, contrôle ; client LLM compatible OpenAI (OpenRouter/Gemini) | S04-S05 |
| `plugin/bridge/` | Serveur HTTP local (127.0.0.1, port aléatoire, jeton) appelé par le MCP ; marshalling vers le thread principal Qt | S01 |
| `plugin/geofunc/` | Outils SIG PyQGIS — Processing-first (`native:*`), validation des paramètres, niveaux de risque ; registre d'artefacts (réutilisation des sorties par nom) | S02, S11 |
| `plugin/core/` | Configuration, journal SQLite (prompts LLM inclus), erreurs structurées, `compat.py` (QGIS 3.40→3.44) | S00-S07 |
| `mcp_server/` | Serveur MCP stdio ; chaque tool = wrapper HTTP vers le bridge | S03 |
| `common/` | Code partagé **sans dépendance QGIS** : config, schémas JSON, codes d'erreur — testable partout | S00+ |
| `tests/` | Tests pytest ; intégration QGIS via `qgis.testing` + CI Docker (RT8) | S06+ |

## Décisions structurantes (rappel)

- **D-01** — le bridge HTTP est embarqué dans le plugin : PyQGIS n'existe que dans le
  processus QGIS ; le MCP reste un processus séparé et testable.
- **D-02** — cible QGIS 3.44 LTR, minimum 3.40 ; toute API versionnée passe par
  `plugin/core/compat.py` (RT9).
- **D-03** — LLM interchangeable (OpenRouter/Gemini free tier) via abstraction
  compatible OpenAI, configuré dans `.env` (jamais committé).
- **D-06** — journal SQLite (WAL) dans le profil QGIS, incluant prompts/réponses LLM (RT4).

## Règles de robustesse applicables à l'architecture

| ID | Règle | Où elle s'applique |
|---|---|---|
| RT1 | Processing-first | `plugin/geofunc/` |
| RT3 | Dry-run avant exécution | `plugin/agent/` (plan) |
| R3 | Retries limités + backoff (erreurs transitoires), politique par étape | `plugin/agent/retry.py`, `plugin/agent/orchestrator.py`, `plugin/agent/llm.py` |
| RT6 | Sorties anti-collision | `plugin/geofunc/` (écritures) |
| RT7 | Sanitisation du contexte LLM | `plugin/agent/` |
| RT9 | `compat.py` pour toute API QGIS | `plugin/core/compat.py` |

## Flux d'une requête (cible MVP)

1. L'utilisateur tape une instruction dans `plugin/ui/`.
2. `plugin/agent/` interroge le contexte via le MCP → bridge → `plugin/geofunc/`.
3. L'agent produit un plan JSON (étapes, outils, paramètres, niveau de risque).
4. Validation humaine dans l'interface (§16 du CDC).
5. Exécution séquentielle, arrêt à la première erreur, contrôle des résultats.
6. Journalisation SQLite + restitution du résumé.

## Réutilisation des sorties intermédiaires (S11 — V2)

```text
Étape 1 : buffer(layer="routes", output="routes_buffer")
        → produit <out>/routes_buffer_teranga_*.gpkg
        → enregistré comme artefact "routes_buffer" + ajouté au projet QGIS

Étape 2 : clip(input="villages", overlay="routes_buffer")
        → le bridge résout "routes_buffer" via le registre d'artefacts
          (plugin/geofunc/artifacts.py) puis la couche du projet
        → aucune rechargement manuel de fichier
```

- `plugin/geofunc/artifacts.py` : `ArtifactStore` (nom logique → chemin + métadonnées),
  module pur (sans QGIS), durée de vie = session du bridge.
- `plugin/geofunc/layer_resolver.py` : `ensure_layer_in_project()` résout une référence
  dans l'ordre **artefact → couche du projet → chemin de fichier** et ajoute la couche
  produite au projet sous son nom logique.
- Bridge (`plugin/bridge/bridge.py`) : `_execute_tool_sync` normalise les paramètres de
  sortie (nom logique → chemin horodaté), résout les paramètres de couche, enregistre
  l'artefact produit et renvoie `artifact` dans les données du résultat ; `GET /v1/artifacts`
  expose le registre de session.

## Reprise contrôlée et mémoire de conversation (S13 — V2)

```text
Panneau chat (plugin/ui/chat_panel.py)
    ├─ Conversation (plugin/agent/conversation.py, module pur)
    │    → historique (tours+artefacts) injecté dans GeoAgent.plan(...)
    └─ exécution → échec récupérable
           → _confirm_repair() (validation humaine)
           → GeoAgent.repair(étape échouée) — UNE seule tentative
           → ré-exécution du plan corrigé via l'orchestrateur
```

- `plugin/agent/conversation.py` : `Conversation` (nom logique des tours → messages LLM),
  budget borné (tours + caractères) ; module pur (testable sans QGIS).
- `plugin/agent/agent.py` : `plan(..., conversation=None)` injecte l'historique ;
  `repair(failed_step, error_message, context)` produit un plan de correction (1 essai).
- `plugin/agent/orchestrator.py` : `resume(plan, previous_report, plan_override=...)`
  reprend l'exécution à l'étape échouée.
- `plugin/ui/chat_panel.py` : `_RepairWorker` + `_on_repaired` ; la reprise est proposée
  une seule fois (`_repaired_once`), jamais automatique.

## Contrôle d'exécution — progression et annulation (S14 — V2)

```text
Panneau chat (plugin/ui/chat_panel.py)
    ├─ _ExecWorker (QThread) → Orchestrator.run(on_step_start, should_cancel)
    │      ├─ step_started(index, total, outil) → statut « étape i/n : outil »
    │      └─ cancel_event (threading.Event) → should_cancel() (lu par l'orchestrateur)
    └─ bouton « Annuler » → cancel() → cancel_event.set()
```

- `plugin/agent/orchestrator.py` : `run(..., on_step_start, on_step_finished, should_cancel)`
  et `ExecutionReport.cancelled`. L'annulation est **coopérative** : vérifiée entre les
  étapes et avant chaque nouvelle tentative, jamais au milieu d'une étape Processing.
- `plugin/ui/chat_panel.py` : `_ExecWorker.step_started` + `cancel()` ; `format_execution`
  affiche « (exécution annulée par l'utilisateur) ».

## Conventions de code
- Aucune dépendance externe dans `plugin/` au-delà de ce que QGIS embarque.
- `common/` ne doit jamais importer `qgis.*` (permet les tests sans QGIS).
- Erreurs : exceptions structurées + codes d'erreur partagés, messages en français.
