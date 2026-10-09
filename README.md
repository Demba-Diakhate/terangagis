# TerangaGIS

Agent GeoAI pour QGIS : réalise des tâches SIG à partir d'instructions en langage naturel.

> **Statut du projet : MVP livré (S00–S10, version 1.0.0) ; V2 « Workflow Agent » en cours (S14)** — voir [`PROJECT_STATUS.md`](PROJECT_STATUS.md)
> **Document de référence :** cahier des charges combiné V2.0 (`../TerangaGIS_Cahier_des_charges_Combine_V2.md`)
> **Guide utilisateur :** [`docs/guide_utilisateur.md`](docs/guide_utilisateur.md)

## Principe

```text
Instruction naturelle → compréhension → plan → validation → QGIS → résultat → journalisation
```

TerangaGIS n'est ni un simple chatbot ni un simple serveur MCP : c'est un **agent GeoAI**
qui inspecte le projet, construit un plan, demande confirmation pour les opérations à risque,
exécute via QGIS Processing et journalise chaque action.

## Chaînage par nom des sorties (S11)

Pour un workflow multi-étapes, chaque étape productrice peut nommer sa sortie
(paramètre `output`, ex. `routes_buffer`) ; les étapes suivantes la référencent par
ce nom (`layer`, `input`, `overlay`, `from`, `to`). Le bridge (côté QGIS) résout la
référence via le registre d'artefacts de session (`plugin/geofunc/artifacts.py`),
ajoute la couche produite au projet et renvoie son nom dans le champ `artifact` —
aucun rechargement manuel de fichier n'est nécessaire. Le registre est consultable
via `GET /v1/artifacts`.

## Exécution robuste (S12)

Les erreurs sont classées `transient` / `permanent` (`plugin/agent/retry.py`) :

- retries limités avec backoff exponentiel pour les erreurs transitoires, par étape
  (`TERANGA_STEP_MAX_RETRIES`, `TERANGA_LLM_BACKOFF`) ;
- politique `stop` (défaut) ou `continue` par étape (`AgentStep.on_error`) ;
- côté LLM, les 4xx ne sont pas réessayés, 429/5xx/timeout le sont (avec `Retry-After`) ;
- l'agent redemande une correction si le plan n'est pas exploitable (`parse_retries`).

## Mémoire de conversation et reprise (S13)

- Mémoire de conversation de session (`plugin/agent/conversation.py`, module **pur**) :
  l'historique des échanges et les artefacts produits sont réinjectés dans le prompt
  (budget borné) pour permettre les demandes de suivi (« et maintenant ? »).
- **Reprise contrôlée** : si une étape échoue avec une erreur *récupérable*
  (`Orchestrator.resume`), l'interface propose **une seule** correction LLM de l'étape
  (`GeoAgent.repair`), ré-exécutée après accord de l'utilisateur. Aucune boucle automatique.
- La mémoire de conversation ne vit que pendant la session du panneau (aucune persistance).

## Contrôle d'exécution (S14)

- **Progression** : l'orchestrateur notifie le début et la fin de chaque étape
  (`on_step_start` / `on_step_finished`) ; le panneau affiche « étape i/n : outil ».
- **Annulation** : le bouton **Annuler** du panneau pose un drapeau (`should_cancel`)
  vérifié par l'orchestrateur **entre les étapes** (et entre deux tentatives). L'arrêt
  est coopératif — une étape Processing déjà lancée va jusqu'au bout — puis le rapport
  porte `cancelled=True` et l'interface affiche « Exécution annulée. ».

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
│   ├── core/            # configuration, erreurs, compatibilité
│   ├── geofunc/         # outils SIG PyQGIS + catalogue (16 outils)
│   ├── bridge/          # serveur HTTP local (jeton de session)
│   ├── agent/           # LLM, planification, validation, orchestrateur, journal
│   ├── workflows/       # 3 workflows métier (S08)
│   └── ui/              # panneau de dialogue (chat)
├── mcp/                 # serveur MCP stdio + client bridge
├── common/              # code partagé sans dépendance QGIS (config, schémas)
├── tests/               # tests (pytest) + smokes QGIS + corpus golden
├── docs/                # documentation technique et utilisateur
├── scripts/             # scripts d'installation/dev + évaluation corpus
├── Dockerfile.ci        # image CI reproductible (qgis/qgis, RT8)
└── .github/workflows/   # CI GitHub Actions
```

## Installation du plugin (développement)

1. Installer QGIS 3.44 LTR depuis <https://qgis.org> (onglet Download → LTR).
2. Installer le plugin (avec ses paquets embarqués `common` et `mcp`) :

```powershell
# Windows (PowerShell)
powershell -ExecutionPolicy Bypass -File scripts/install_plugin.ps1
```

```bash
# Linux / macOS
python scripts/build_plugin.py            # génère dist/terangagis-<version>.zip
# puis décompresser l'archive dans le dossier des extensions du profil QGIS
```

3. Redémarrer QGIS → Extensions → Gérer les extensions → activer **TerangaGIS**.

## Packaging (release)

```bash
python scripts/build_plugin.py   # produit dist/terangagis-<version>.zip (installable dans QGIS)
```

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
la qualité de l'agent est mesurée par un corpus golden exécuté séparément.

### Corpus golden (RT2, hors CI)

```bash
python scripts/run_golden.py --validate   # structure du corpus
python scripts/run_golden.py --fake       # auto-test de la notation (sans LLM)
python scripts/run_golden.py              # évaluation réelle (clé LLM requise)
```

### Smokes PyQGIS (QGIS requis)

```bash
"C:/Program Files/QGIS 3.44.15/bin/python-qgis-ltr.bat" tests/tools_smoke.py
"C:/Program Files/QGIS 3.44.15/bin/python-qgis-ltr.bat" tests/bridge_http_smoke.py
"C:/Program Files/QGIS 3.44.15/bin/python-qgis-ltr.bat" tests/artifacts_smoke.py
"C:/Program Files/QGIS 3.44.15/bin/python-qgis-ltr.bat" tests/workflows_smoke.py
```

### CI Docker (RT8)

```bash
docker build -f Dockerfile.ci -t terangagis-ci .
docker run --rm terangagis-ci
```

## Règles de travail

- Lire `PROJECT_STATUS.md` **avant** toute modification (agent IA comme humain).
- Une tâche n'est `FAIT` que si DoD vérifiée + tests verts + statut mis à jour.
- Processing-first (RT1), sorties anti-collision (RT6), compatibilité via `plugin/core/compat.py` (RT9).

## Convention de contribution

Git : branches par sprint (`sprint/00-preparation`), commits explicites,
une fonctionnalité par commit avec son test.
