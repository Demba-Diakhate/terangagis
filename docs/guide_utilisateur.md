# Guide utilisateur — TerangaGIS

TerangaGIS est un agent GeoAI intégré à QGIS : vous décrivez une tâche SIG en
français, il inspecte le projet, propose un plan, le valide, exécute via QGIS
Processing et journalise chaque action.

## 1. Prérequis

| Outil | Version |
|---|---|
| QGIS | 3.44 LTR (minimum 3.40) |
| Clé LLM | OpenRouter **ou** Google Gemini (offre gratuite) |

## 2. Installation du plugin

Deux méthodes :

**A. Depuis le paquet de release** : décompresser `dist/terangagis-<version>.zip`
dans le dossier des extensions du profil QGIS (il contient un dossier `terangagis/`).

**B. Depuis les sources (développement)** :

```powershell
powershell -ExecutionPolicy Bypass -File scripts/install_plugin.ps1
```

Le script copie le plugin et ses paquets embarqués (`common`, `mcp`) sous le nom
`terangagis` dans le profil QGIS.

3. Redémarrer QGIS → **Extensions → Gérer les extensions** → activer **TerangaGIS**.

## 3. Configuration de la clé LLM

Créer un fichier `.env` à la racine du dépôt (ou définir les variables
d'environnement) à partir de `.env.example` :

```bash
cp .env.example .env
```

Renseigner **une** des clés : `OPENROUTER_API_KEY` ou `GEMINI_API_KEY`.
Le fichier `.env` est ignoré par Git : ne jamais committer de secret.

## 4. Utilisation

1. Charger vos couches dans QGIS.
2. Ouvrir le panneau **TerangaGIS** (icône barre d'outils ou menu Extensions).
3. Saisir une instruction en français, par exemple :
   - « Fais un tampon de 5 km autour des routes. »
   - « Identifie les villages situés à plus de 10 km d'un poste de santé. »
   - « Nettoie cette couche GPS et corrige les géométries. »
4. TerangaGIS affiche le **plan** et le résultat de la **validation**.
5. Pour les opérations qui écrivent des données, une **confirmation** est demandée.
6. Le résultat s'affiche dans le panneau et les couches produites sont ajoutées au projet.

## 5. Workflows métier prêts à l'emploi

| Workflow | Couches requises | Enchaînement |
|---|---|---|
| Accessibilité aux routes | `routes`, `villages` | `buffer` (5 km) → `clip` |
| Nettoyage de données GPS | `gps` | `fix_geometries` → `remove_duplicates` → `save_layer` |
| Accessibilité aux postes de santé | `villages`, `sante` | `distance_analysis` (euclidien) → `select_by_attribute` (> 10 km) |

## 6. Sécurité et bonnes pratiques

- Le connecteur HTTP est local (`127.0.0.1`), sur un port aléatoire, protégé par un
  **jeton de session** ; il n'écoute jamais sur le réseau.
- Les **sorties ne remplacent jamais** une source du projet (suffixes horodatés, RT6).
- Les opérations à risque (écriture de fichier, modification) demandent confirmation.
- Seules des données tronquées sont transmises au LLM (sanitisation, RT7).
- Vérifiez le **CRS** des couches avant toute opération métrique (un avertissement
  s'affiche si la couche est en degrés).

## 7. Journal et traçabilité

Chaque interaction (prompt/réponse LLM, plan, validation, exécutions) est
journalisée dans une base SQLite. Elle peut être consultée/exportée via
`Journal.recent()` / `Journal.export()` (module `plugin/agent/journal.py`).

## 8. Dépannage

| Symptôme | Cause probable / solution |
|---|---|
| « Agent indisponible » | Clé LLM absente ou invalide (voir §3) |
| Avertissement CRS géographique | Reprojeter la couche en UTM (`reproject_layer`) |
| Sortie non créée | Vérifier les unités/CRS et le répertoire de sortie |
| Le panneau ne répond pas | Attendre la fin de l'étape (LLM/bridge en arrière-plan) |

## 9. Désinstallation

Désactiver **TerangaGIS** dans le gestionnaire d'extensions, puis supprimer le
dossier `terangagis` du profil QGIS.
