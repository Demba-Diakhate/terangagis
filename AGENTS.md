# AGENTS.md — Règles pour l'agent IA développeur de TerangaGIS

Ce fichier est le **point d'entrée obligatoire** de tout agent IA développant TerangaGIS.

## Lecture obligatoire avant toute modification

1. `PROJECT_STATUS.md` — état courant du projet (sprint, tâche, prochaine action, bloqueurs)
2. Ce fichier (`AGENTS.md`) — règles de travail
3. `README.md` — architecture et conventions (lorsqu'il existe)
4. Le cahier des charges combiné : `../TerangaGIS_Cahier_des_charges_Combine_V2.md` (document de référence unique, V2.0)

**Si `PROJECT_STATUS.md` n'a pas été lu, aucune modification de code n'est autorisée.**

## Système de suivi agile

- `PROJECT_STATUS.md` est la **source de vérité** de l'avancement.
- Statuts possibles : `À FAIRE` | `EN COURS` | `FAIT` | `BLOQUÉ`
- Mettre à jour le statut **à chaque changement d'état**, pas seulement en fin de session.
- Une tâche passe à `FAIT` uniquement si :
  - sa DoD est vérifiée ;
  - les tests sont verts ;
  - `PROJECT_STATUS.md` a été mis à jour.
- Une session commence par lire l'état et se termine par le mettre à jour (section « Historique des sessions »).

## Règles de travail

1. Un seul sprint à la fois ; ne pas commencer le suivant tant que la DoD du courant n'est pas satisfaite.
2. Ne pas modifier plusieurs composants majeurs sans validation de l'utilisateur.
3. Écrire les tests **avec** les nouvelles fonctionnalités.
4. Ne jamais supprimer de fonctionnalités existantes sans justification écrite.
5. Documenter les décisions importantes dans `PROJECT_STATUS.md` (section « Décisions techniques »).
6. Signaler les hypothèses et les points ouverts.
7. Exécuter les tests avant de déclarer une tâche terminée.
8. Fournir un résumé des fichiers modifiés à la fin de chaque tâche.
9. Ne jamais exposer de secrets ; aucun dans le dépôt, uniquement dans `.env` (ignoré par Git).
10. Conserver une architecture modulaire.

## Règles techniques (références du cahier des charges V2.0)

| ID | Règle |
|---|---|
| RT1 | **Processing-first** : utiliser les algorithmes QGIS Processing (`native:*`) ; pas de code géométrique maison sans justification. |
| RT2 | **Corpus golden** : préserver/étendre le corpus d'évaluation instruction → appels attendus (hors CI). |
| RT3 | **Dry-run** : valider le plan (params, CRS, sorties) avant exécution. |
| RT4 | **Journal LLM** : journaliser prompts/réponses LLM dans SQLite. |
| RT5 | **Distance euclidienne** : seule sémantique de `distance_analysis` dans le MVP. |
| RT6 | **Sorties anti-collision** : jamais écrire sur une source du projet ; suffixe `_teranga_YYYYMMDD` ou `resultats_terangagis.gpkg`. |
| RT7 | **Sanitisation** : tronquer/échapper les valeurs attributaires envoyées au LLM. |
| RT8 | **CI Docker `qgis/qgis`** : tests headless reproductibles. |
| RT9 | **compat.py** : toute API QGIS versionnée passe par le module de compatibilité (cible 3.40 → 3.44). |

## Exigences transverses

- **CRS/units** : vérifier le CRS de toute couche avant opération métrique ; afficher les unités dans le plan (règle R1 du CDC).
- **Thread principal QGIS** : aucune opération PyQGIS hors thread principal ; marshalling via signaux Qt queued ; tâches longues via `QgsTask` (R6).
- **Sécurité** : bridge HTTP en `127.0.0.1` uniquement, port aléatoire, jeton de session ; confirmations obligatoires pour les opérations niveau élevé/critique.
- **Langue** : interface et messages en français.

## Definition of Done globale

Une fonctionnalité est terminée lorsque : code écrit, testé, erreurs principales gérées, documentation mise à jour, paramètres validés, opérations sensibles protégées, workflow reproductible, code versionné, `PROJECT_STATUS.md` mis à jour, et utilisable par un agent IA sans intervention manuelle du développeur.

## Format des tâches

```text
SPRINT: SPRINT-03
TASK: MCP-003

Objectif:
Exposer l'outil buffer via MCP.

Entrées:
- layer_id
- distance
- dissolve
- output

Contraintes:
- ne pas modifier la couche originale ;
- valider distance > 0 ;
- retourner une erreur structurée.

Tests:
- buffer valide ;
- distance invalide ;
- couche inexistante ;
- fichier de sortie invalide.

Definition of Done:
- code ;
- tests ;
- documentation ;
- démonstration ;
- PROJECT_STATUS.md mis à jour.
```
