"""Agent IA minimal (squelette S03)."""
from __future__ import annotations
from dataclasses import dataclass
from typing import Any, List
@dataclass
class AgentStep:
    tool: str
    params: dict[str, Any]
@dataclass
class AgentPlan:
    steps: List[AgentStep]
class GeoAgent:
    def __init__(self) -> None:
        pass
    def plan(self, user_query: str) -> AgentPlan:
        return AgentPlan(steps=[])
