from __future__ import annotations

from dataclasses import asdict, dataclass


@dataclass(frozen=True)
class ToolError:
    """Unified error payload for tools and services."""

    success: bool
    error_type: str
    message: str
    raw_error: str | None = None

    def to_dict(self) -> dict:
        return asdict(self)
