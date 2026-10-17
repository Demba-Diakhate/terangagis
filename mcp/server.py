"""Serveur MCP TerangaGIS (stdio, JSON-RPC 2.0).

Expose les outils SIG du bridge QGIS comme tools MCP.
Variables d'environnement :
  - TERANGA_BRIDGE_URL : ex. http://127.0.0.1:51234
  - TERANGA_TOKEN      : jeton de session X-Teranga-Token
"""
from __future__ import annotations

import json
import os
import sys
from typing import Any

from mcp.bridge_client import BridgeClient, BridgeClientError

PROTOCOL_VERSION = "2024-11-05"
SERVER_NAME = "terangagis"
SERVER_VERSION = "0.1.0"

TOOL_SCHEMAS: dict[str, dict[str, Any]] = {
    "get_project_info": {"description": "Informations sur le projet QGIS courant", "properties": {}},
    "list_layers": {"description": "Liste des couches du projet", "properties": {}},
    "get_layer_info": {"description": "Détails d'une couche (option `profile` : statistiques élémentaires et qualité)", "properties": {"name": {"type": "string"}, "profile": {"type": "boolean", "description": "Inclure un profil de données (statistiques par champ + résumé qualité)"}}, "required": ["name"]},
    "get_selected_features": {"description": "Entités sélectionnées par couche", "properties": {}},
    "reproject_layer": {"description": "Reprojette une couche vers un CRS cible", "properties": {"layer": {"type": "string"}, "target_crs": {"type": "string"}, "output": {"type": "string", "description": "Nom logique ou chemin de sortie (ex. 'routes_utm')"}}, "required": ["layer", "target_crs"]},
    "fix_geometries": {"description": "Corrige les géométries invalides", "properties": {"layer": {"type": "string"}, "output": {"type": "string", "description": "Nom logique ou chemin de sortie"}}, "required": ["layer"]},
    "remove_duplicates": {"description": "Supprime les entités dupliquées", "properties": {"layer": {"type": "string"}, "fields": {"type": "array"}, "output": {"type": "string", "description": "Nom logique ou chemin de sortie"}}, "required": ["layer"]},
    "select_by_attribute": {"description": "Sélectionne par expression attributaire", "properties": {"layer": {"type": "string"}, "expression": {"type": "string"}}, "required": ["layer", "expression"]},
    "buffer": {"description": "Tampon euclidien autour d'une couche", "properties": {"layer": {"type": "string"}, "distance": {"type": "number"}, "output": {"type": "string", "description": "Nom logique ou chemin de sortie (ex. 'routes_buffer')"}}, "required": ["layer", "distance"]},
    "clip": {"description": "Découpe une couche par une autre", "properties": {"input": {"type": "string"}, "overlay": {"type": "string"}, "output": {"type": "string", "description": "Nom logique ou chemin de sortie"}}, "required": ["input", "overlay"]},
    "intersection": {"description": "Intersection de deux couches", "properties": {"input": {"type": "string"}, "overlay": {"type": "string"}, "output": {"type": "string", "description": "Nom logique ou chemin de sortie"}}, "required": ["input", "overlay"]},
    "dissolve": {"description": "Dissout les entités d'une couche", "properties": {"layer": {"type": "string"}, "output": {"type": "string", "description": "Nom logique ou chemin de sortie"}}, "required": ["layer"]},
    "spatial_join": {"description": "Jointure spatiale", "properties": {"input": {"type": "string"}, "join": {"type": "string"}, "output": {"type": "string", "description": "Nom logique ou chemin de sortie"}}, "required": ["input", "join"]},
    "distance_analysis": {"description": "Matrice de distances euclidiennes", "properties": {"from": {"type": "string"}, "to": {"type": "string"}, "output": {"type": "string", "description": "Nom logique ou chemin de sortie"}}, "required": ["from", "to"]},
    "save_layer": {"description": "Enregistre une couche", "properties": {"layer": {"type": "string"}, "path": {"type": "string"}}, "required": ["layer", "path"]},
    "export_map": {"description": "Exporte la carte en PNG", "properties": {"output": {"type": "string"}}},
    "find_senegal_sources": {"description": "Catalogue de sources géospatiales pour le Sénégal (communes, réseau routier, hydrographie) : métadonnées, mots-clés et CRS suggéré (EPSG:32628). Le catalogue décrit des sources recommandées — les couches doivent être chargées par l'utilisateur.", "properties": {"query": {"type": "string", "description": "Mot-clé de recherche (ex. 'route', 'commune', 'hydro') ; optionnel (sans query, toutes les sources sont listées)"}}, },
}


def _tool_defs() -> list[dict[str, Any]]:
    defs = []
    for name, spec in TOOL_SCHEMAS.items():
        defs.append({
            "name": name,
            "description": spec.get("description", ""),
            "inputSchema": {
                "type": "object",
                "properties": spec.get("properties", {}),
                "required": spec.get("required", []),
            },
        })
    return defs


class MCPServer:
    def __init__(self, client: BridgeClient | None = None) -> None:
        self.client = client or self._client_from_env()

    def _client_from_env(self) -> BridgeClient:
        url = os.environ.get("TERANGA_BRIDGE_URL", "http://127.0.0.1:0")
        token = os.environ.get("TERANGA_TOKEN", "")
        return BridgeClient(url, token)

    def handle(self, message: dict[str, Any]) -> dict[str, Any] | None:
        method = message.get("method")
        msg_id = message.get("id")
        if method == "initialize":
            return self._result(msg_id, {
                "protocolVersion": PROTOCOL_VERSION,
                "capabilities": {"tools": {}},
                "serverInfo": {"name": SERVER_NAME, "version": SERVER_VERSION},
            })
        if method in ("notifications/initialized", "initialized"):
            return None
        if method == "tools/list":
            return self._result(msg_id, {"tools": _tool_defs()})
        if method == "tools/call":
            return self._handle_tool_call(msg_id, message.get("params") or {})
        if method == "ping":
            return self._result(msg_id, {})
        return self._error(msg_id, -32601, f"Méthode inconnue : {method}")

    def _handle_tool_call(self, msg_id: Any, params: dict[str, Any]) -> dict[str, Any]:
        tool = params.get("name")
        args = params.get("arguments") or {}
        if tool not in TOOL_SCHEMAS:
            return self._error(msg_id, -32602, f"Outil inconnu : {tool}")
        try:
            result = self.client.execute(tool, args)
        except BridgeClientError as e:
            return self._result(msg_id, {
                "isError": True,
                "content": [{"type": "text", "text": f"Erreur bridge : {e}"}],
            })
        text = json.dumps(result, ensure_ascii=False, indent=2)
        return self._result(msg_id, {
            "isError": not result.get("ok", False),
            "content": [{"type": "text", "text": text}],
        })

    @staticmethod
    def _result(msg_id: Any, result: Any) -> dict[str, Any]:
        return {"jsonrpc": "2.0", "id": msg_id, "result": result}

    @staticmethod
    def _error(msg_id: Any, code: int, message: str) -> dict[str, Any]:
        return {"jsonrpc": "2.0", "id": msg_id, "error": {"code": code, "message": message}}

    def serve_stdio(self) -> None:
        for line in sys.stdin:
            line = line.strip()
            if not line:
                continue
            try:
                message = json.loads(line)
            except json.JSONDecodeError:
                continue
            response = self.handle(message)
            if response is not None:
                sys.stdout.write(json.dumps(response, ensure_ascii=False) + "\n")
                sys.stdout.flush()


def main() -> None:
    MCPServer().serve_stdio()


if __name__ == "__main__":
    main()