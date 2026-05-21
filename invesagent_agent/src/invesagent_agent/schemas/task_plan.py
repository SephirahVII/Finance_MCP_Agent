from __future__ import annotations

from typing import Literal, TypedDict


class TaskPlan(TypedDict, total=False):
    """Structured research task plan."""

    task_type: Literal["company_research", "industry_research", "mixed_research"]
    query: str
    symbols: list[str]
    industry: str | None
    start_date: str
    end_date: str
    modules: list[str]
    research_questions: list[str]
    data_needs: list[str]
    constraints: list[str]
    notes: list[str]
