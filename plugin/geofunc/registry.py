"""Registre d'outils SIG."""
from __future__ import annotations
from typing import Type
from .tool_base import GeoTool
class ToolRegistry:
    def __init__(self) -> None: self._tools = {}
    def register(self, cls: Type[GeoTool]) -> None: self._tools[cls.name] = cls
    def get(self, name: str) -> Type[GeoTool] | None: return self._tools.get(name)
    def list(self) -> list[str]: return sorted(self._tools.keys())
