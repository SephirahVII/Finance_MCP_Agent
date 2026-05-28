from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class AgentMemory:
    """Structured session memory shared by chat and research workflows."""

    last_query: str = ""
    last_task_plan: dict[str, Any] = field(default_factory=dict)
    last_required_agents: list[str] = field(default_factory=list)
    last_symbols: list[str] = field(default_factory=list)
    last_industry: str | None = None
    last_date_range: dict[str, Any] = field(default_factory=dict)
    last_warnings: list[str] = field(default_factory=list)
    last_outputs: dict[str, Any] = field(default_factory=dict)
    unresolved_clarification: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_value(cls, value: Any) -> "AgentMemory":
        if isinstance(value, cls):
            return value
        if not isinstance(value, dict):
            return cls()
        return cls(
            last_query=str(value.get("last_query") or ""),
            last_task_plan=dict(value.get("last_task_plan") or {}),
            last_required_agents=[
                str(item) for item in value.get("last_required_agents", []) if item
            ],
            last_symbols=[str(item) for item in value.get("last_symbols", []) if item],
            last_industry=value.get("last_industry"),
            last_date_range=dict(value.get("last_date_range") or {}),
            last_warnings=[str(item) for item in value.get("last_warnings", []) if item],
            last_outputs=dict(value.get("last_outputs") or {}),
            unresolved_clarification=dict(value.get("unresolved_clarification") or {}),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "last_query": self.last_query,
            "last_task_plan": self.last_task_plan,
            "last_required_agents": self.last_required_agents,
            "last_symbols": self.last_symbols,
            "last_industry": self.last_industry,
            "last_date_range": self.last_date_range,
            "last_warnings": self.last_warnings,
            "last_outputs": self.last_outputs,
            "unresolved_clarification": self.unresolved_clarification,
        }

    def for_prompt(self) -> dict[str, Any]:
        return {
            "last_query": self.last_query,
            "last_task_plan": self.last_task_plan,
            "last_required_agents": self.last_required_agents,
            "last_symbols": self.last_symbols,
            "last_industry": self.last_industry,
            "last_date_range": self.last_date_range,
            "unresolved_clarification": self.unresolved_clarification,
        }


def normalize_agent_memory(value: Any) -> dict[str, Any]:
    return AgentMemory.from_value(value).to_dict()
