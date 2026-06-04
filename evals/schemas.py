from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class EvalCase:
    id: str
    query: str
    category: str = "general"
    benchmark: str = "l1"
    expected: dict[str, Any] = field(default_factory=dict)
    messages: list[dict[str, str]] | None = None
    task_memory: dict[str, Any] | None = None

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> "EvalCase":
        return cls(
            id=str(value["id"]),
            query=str(value.get("query") or ""),
            category=str(value.get("category") or "general"),
            benchmark=str(value.get("benchmark") or "l1"),
            expected=dict(value.get("expected") or {}),
            messages=value.get("messages"),
            task_memory=value.get("task_memory"),
        )
