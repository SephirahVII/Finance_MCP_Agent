from __future__ import annotations

from typing import Any, Literal, TypedDict


Confidence = Literal["low", "medium", "high"]


class AnalystOutput(TypedDict, total=False):
    """Common structured analysis shape returned by LLM analyst nodes."""

    summary: str
    key_findings: list[str]
    strengths: list[str]
    risks: list[str]
    data_limits: list[str]
    confidence: Confidence
    reasoning_summary: list[str]
    raw_context: dict[str, Any]
