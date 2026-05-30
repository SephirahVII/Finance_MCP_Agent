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
    user_date_range: dict[str, Any]
    date_ranges: dict[str, dict[str, str]]
    provider: str
    industry_member_limit: int
    messages: list[dict[str, str]]
    task_memory: dict[str, Any]
    tool_client: Any
    required_agents: list[str]

    data_package: dict[str, Any]
    price_volume_analysis: dict[str, Any]
    fundamental_analysis: dict[str, Any]
    industry_analysis: dict[str, Any]
    macro_policy_analysis: dict[str, Any]
    valuation_analysis: dict[str, Any]
    report_review: dict[str, Any]
    review_round: int

    charts: list[dict[str, Any]]
    report_context: dict[str, Any]
    draft_report: str
    review_comments: list[str]
    final_response: str
    final_report: str
    trace: list[dict[str, Any]]
    run_report: dict[str, Any]
    warnings: list[str]
