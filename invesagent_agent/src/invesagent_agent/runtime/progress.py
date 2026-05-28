from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol


class ProgressEmitter(Protocol):
    """Emit user-facing workflow progress events."""

    def emit(self, *, node: str, message: str, payload: dict[str, Any] | None = None) -> None:
        ...


@dataclass
class MemoryProgressEmitter:
    """Collect progress events in memory for CLI, tests, or future frontends."""

    events: list[dict[str, Any]] = field(default_factory=list)

    def emit(self, *, node: str, message: str, payload: dict[str, Any] | None = None) -> None:
        self.events.append({"node": node, "message": message, "payload": payload or {}})


@dataclass
class ConsoleProgressEmitter:
    """Print concise progress events to the console."""

    prefix: str = "progress"

    def emit(self, *, node: str, message: str, payload: dict[str, Any] | None = None) -> None:
        print(f"[{self.prefix}:{node}] {message}")


def get_progress_emitter(value: Any = None) -> ProgressEmitter | None:
    if value is not None and hasattr(value, "emit"):
        return value
    return None

