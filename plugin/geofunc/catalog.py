"""Catalogue des outils SIG exposés (registre central).

Point d'entrée unique pour l'inspection (bridge) et le tool calling (MCP/agent).
"""
from __future__ import annotations
from typing import Any, Dict, List

from .registry import ToolRegistry
from .tools_read_complete import (
    GetProjectInfo,
    ListLayers,
    GetLayerInfo,
    GetSelectedFeatures,
)
from .tools_prepare import (
    ReprojectLayer,
    FixGeometries,
    RemoveDuplicates,
    SelectByAttribute,
)
from .tools_analyze import (
    Buffer,
    Clip,
    Intersection,
    Dissolve,
    SpatialJoin,
    DistanceAnalysis,
)
from .tools_output import SaveLayer, ExportMapPNG

_TOOL_CLASSES = [
    GetProjectInfo,
    ListLayers,
    GetLayerInfo,
    GetSelectedFeatures,
    ReprojectLayer,
    FixGeometries,
    RemoveDuplicates,
    SelectByAttribute,
    Buffer,
    Clip,
    Intersection,
    Dissolve,
    SpatialJoin,
    DistanceAnalysis,
    SaveLayer,
    ExportMapPNG,
]


def build_registry() -> ToolRegistry:
    registry = ToolRegistry()
    for cls in _TOOL_CLASSES:
        registry.register(cls)
    return registry


_REGISTRY = build_registry()


def get_registry() -> ToolRegistry:
    return _REGISTRY


def list_tools() -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    for name in _REGISTRY.list():
        cls = _REGISTRY.get(name)
        out.append({
            'name': cls.name,
            'description': getattr(cls, 'description', ''),
            'category': getattr(cls, 'category', ''),
        })
    return out


def run_tool(name: str, params: Dict[str, Any]):
    cls = _REGISTRY.get(name)
    if cls is None:
        return None
    return cls().run(params or {})