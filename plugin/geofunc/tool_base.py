"""Base commune pour les outils SIG (Processing-first, CDC V2.0 RT1)."""
from __future__ import annotations
from dataclasses import dataclass
from typing import Any
@dataclass(frozen=True)
class ToolResult:
    ok: bool
    data: dict[str, Any] | None = None
    error: dict[str, Any] | None = None
    def to_dict(self) -> dict[str, Any]:
        return {"ok": self.ok, "data": self.data, "error": self.error}
class GeoTool:
    name: str = "geo_tool"
    description: str = "Outil SIG générique"
    def run(self, params: dict[str, Any]) -> ToolResult:
        raise NotImplementedError
