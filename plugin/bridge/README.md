# Bridge HTTP TerangaGIS

Serveur HTTP local embarqué dans QGIS (Sprint 1). 

- Écoute uniquement `127.0.0.1`, port aléatoire, jeton `X-Teranga-Token` par session
- Exécution des opérations sur le thread principal Qt (marshalling)
- Endpoints d'inspection : `/health`, `/v1/project`, `/v1/layers`, `/v1/layers/{name}/info`, `/v1/layers/selected`

## Démarrage (depuis le plugin QGIS)

```python
from plugin.bridge.bridge import BridgeServer

bridge = BridgeServer()
info = bridge.start()  # {base_url, token, port}
# conserver bridge vivant
```

## Appel avec authentification

```http
GET http://127.0.0.1:<port>/v1/project
X-Teranga-Token: <token>
```

Réponses : `{ok: true, data: {...}}` ou `{ok: false, error: {code, message, details}}`.
