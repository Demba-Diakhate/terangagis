# TerangaGIS

Agent GeoAI pour QGIS : réalise des tâches SIG à partir d'instructions en langage naturel.

> **Statut du projet : Sprint 0 (Préparation)** — voir [`PROJECT_STATUS.md`](PROJECT_STATUS.md)
> **Document de référence :** cahier des charges combiné V2.0 (`../TerangaGIS_Cahier_des_charges_Combine_V2.md`)

## Principe

```text
Instruction naturelle → compréhension → plan → validation → QGIS → résultat → journalisation
```

TerangaGIS n'est ni un simple chatbot ni un simple serveur MCP : c'est un **agent GeoAI**
qui inspecte le projet, construit un plan, demande confirmation pour les opérations à risque,
exécute via QGIS Processing et journalise chaque action.

## Prérequis

| Outil | Version |
|---|---|
| QGIS | **3.44 LTR** (minimum 3.40) |
| Python | embarqué avec QGIS ; Python 3.13+ pour les tests hors QGIS |
| Git | toute version récente |
| LLM | clé gratuite OpenRouter **ou** Gemini (free tier) — voir `.env.example` |

## Structure du dépôt

```text
terangagis/
├── AGENTS.md            # règles de l'agent IA développeur (lire en premier)
├── PROJECT_STATUS.md    # tableau de bord agile (sprint, tâches, décisions)
├── plugin/              # plugin QGIS (racine = dossier installé dans QGIS)
│   ├── metadata.txt     # qgisMinimumVersion=3.40
│   ├── core/            # configuration, journal, erreurs, compatibilité
│   ├── geofunc/         # outils SIG PyQGIS (cœur exécutable)
│   ├── bridge/          # serveur HTTP local (Sprint 1)
│   ├── agent/           # boucle agent + client LLM (Sprint 4)
│   └── ui/              # panneau chat (Sprint 6)
├── mcp_server/          # serveur MCP stdio (Sprint 3)
├── common/              # code partagé sans dépendance QGIS (config, schémas)
├── tests/               # tests (pytest, sans LLM)
├── docs/                # documentation technique
└── scripts/             # scripts d'installation/dev
```

## Installation du plugin (développement)

1. Installer QGIS 3.44 LTR depuis <https://qgis.org> (onglet Download → LTR).
2. Copier le dossier `plugin/` dans le profil QGIS sous le nom `terangagis` :

```powershell
# Windows (PowerShell) — voir aussi scripts/install_plugin.ps1
$profile = "$env:APPDATA\QGIS\QGIS3\profiles\default\python\plugins"
New-Item -ItemType Directory -Force -Path $profile | Out-Null
Copy-Item -Recurse -Force plugin "$profile\terangagis"
```

```bash
# Linux / macOS
cp -r plugin ~/.local/share/QGIS/QGIS3/profiles/default/python/plugins/terangagis
```

3. Redémarrer QGIS → Extensions → Gérer les extensions → activer **TerangaGIS**.

## Configuration LLM

```bash
cp .env.example .env   # puis renseigner OPENROUTER_API_KEY ou GEMINI_API_KEY
```

`.env` est ignoré par Git. Aucun secret ne doit jamais être committé.

## Tests

```bash
pip install -r requirements-dev.txt
pytest
```

Les tests du MVP ne passent **jamais** par un appel LLM en CI (règle RT2) ;
la qualité de l'agent est mesurée par un corpus golden exécuté séparément (Sprint 9).

## Règles de travail

- Lire `PROJECT_STATUS.md` **avant** toute modification (agent IA comme humain).
- Une tâche n'est `FAIT` que si DoD vérifiée + tests verts + statut mis à jour.
- Processing-first (RT1), sorties anti-collision (RT6), compatibilité via `plugin/core/compat.py` (RT9).

## Convention de contribution

Git : branches par sprint (`sprint/00-preparation`), commits explicites,
une fonctionnalité par commit avec son test.
