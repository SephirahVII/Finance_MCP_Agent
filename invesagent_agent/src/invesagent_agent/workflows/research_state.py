from __future__ import annotations

from typing import Any, TypedDict


class ResearchState(TypedDict, total=False):
    """Shared state passed between research workflow agents."""

    user_query: str
    task_plan: dict[str, Any]
    tool_calls: list[dict[str, Any]]
    observations: list[dict[str, Any]]
    analyst_notes: dict[str, Any]
    reasoning_summary: dict[str, Any]
    reflection: dict[str, Any]
    symbols: list[str]
    industry: str | None
    market: str
    asset_type: str
    start_date: str
    end_date: str
    provider: str
    industry_member_limit: int

    data_package: dict[str, Any]
    price_volume_analysis: dict[str, Any]
    fundamental_analysis: dict[str, Any]
    industry_analysis: dict[str, Any]

    charts: list[dict[str, Any]]
    draft_report: str
    review_comments: list[str]
    final_report: str
    warnings: list[str]
