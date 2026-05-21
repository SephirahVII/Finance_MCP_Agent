from __future__ import annotations

from typing import Literal, TypedDict


class ReviewOutput(TypedDict, total=False):
    """Structured review output for the research workflow."""

    status: Literal["ok", "needs_revision", "needs_more_data"]
    summary: str
    issues: list[str]
    missing_data: list[str]
    unsupported_claims: list[str]
    recommended_next_steps: list[str]
    data_limits: list[str]
