from __future__ import annotations

from typing import Any, TypedDict


class ChatState(TypedDict, total=False):
    """State for the outer chat and intent-routing workflow."""

    user_query: str
    raw_user_query: str
    market: str
    asset_type: str
    provider: str
    industry_member_limit: int
    messages: list[dict[str, str]]
    task_memory: dict[str, Any]
    tool_client: Any

    general_decision: dict[str, Any]
    conversation_route: str
    intent: dict[str, Any]
    intent_route: str
    final_response: str
    research_state: dict[str, Any]
    trace: list[dict[str, Any]]
    run_report: dict[str, Any]
    warnings: list[str]
