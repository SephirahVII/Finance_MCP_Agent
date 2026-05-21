from __future__ import annotations

import re
from datetime import date

from invesagent_agent.clients.mcp_client import call_mcp_tool
from invesagent_agent.agents.base import run_llm_json_node
from invesagent_agent.prompts.task_planner import TASK_PLANNER_PROMPT
from invesagent_agent.workflows.research_state import ResearchState


_TS_CODE_RE = re.compile(r"\b\d{6}\.(?:SH|SZ|BJ)\b", re.IGNORECASE)
_DATE_RE = re.compile(r"\d{4}[-/]?\d{2}[-/]?\d{2}")


def _normalize_date(value: str) -> str:
    return value.replace("-", "").replace("/", "")


def _extract_dates(query: str) -> tuple[str, str]:
    matches = [_normalize_date(item) for item in _DATE_RE.findall(query)]

    if len(matches) >= 2:
        return matches[0], matches[1]

    current_year = date.today().year
    return f"{current_year - 1}0101", f"{current_year}1231"


def _extract_symbols(query: str) -> list[str]:
    symbols = [item.upper() for item in _TS_CODE_RE.findall(query)]
    return list(dict.fromkeys([symbol for symbol in symbols if symbol]))


def _extract_industry(query: str) -> str | None:
    try:
        result = call_mcp_tool("list_industries_tool", {"market": "cn", "provider": "auto"})
        industries = result.get("industries", []) if result.get("success") else []
    except Exception:
        industries = []

    matches = [industry for industry in industries if industry and industry in query]
    if matches:
        return sorted(matches, key=len, reverse=True)[0]

    return None


def run_task_planner(state: ResearchState) -> ResearchState:
    """Parse the user query into a simple structured research task plan."""
    query = state["user_query"]
    warnings = list(state.get("warnings", []))
    start_date, end_date = _extract_dates(query)
    symbols = _extract_symbols(query)
    industry = _extract_industry(query)

    if not symbols and query.strip():
        try:
            resolved = call_mcp_tool("resolve_instrument_tool", {"query": query})
            if resolved.get("market") != "unknown" and resolved.get("symbol"):
                symbols = [resolved["symbol"]]
        except Exception:
            symbols = []

    modules = ["report"]
    if symbols:
        modules.extend(["price_volume", "fundamentals"])
    if industry:
        modules.append("industry")

    task_plan = {
        "task_type": "industry_research" if industry else "company_research",
        "query": query,
        "symbols": symbols,
        "industry": industry,
        "start_date": start_date,
        "end_date": end_date,
        "modules": modules,
        "notes": [
            "LangGraph workflow now calls MCP tools through the local MCP client facade.",
        ],
    }
    llm_plan = run_llm_json_node(
        system_prompt=TASK_PLANNER_PROMPT,
        context={
            "user_query": query,
            "heuristic_plan": task_plan,
            "market": state.get("market", "cn"),
            "asset_type": state.get("asset_type", "stock"),
            "provider": state.get("provider", "auto"),
        },
        fallback=task_plan,
        warnings=warnings,
    )

    task_plan = {
        **task_plan,
        **{
            key: value
            for key, value in llm_plan.items()
            if key
            in {
                "task_type",
                "query",
                "symbols",
                "industry",
                "start_date",
                "end_date",
                "modules",
                "research_questions",
                "data_needs",
                "constraints",
                "notes",
                "_llm",
                "_llm_error",
            }
        },
    }
    symbols = [str(symbol).upper() for symbol in task_plan.get("symbols", symbols) if symbol]
    industry = task_plan.get("industry") or industry
    start_date = task_plan.get("start_date", start_date)
    end_date = task_plan.get("end_date", end_date)

    return {
        **state,
        "task_plan": task_plan,
        "symbols": symbols,
        "industry": industry,
        "market": state.get("market", "cn"),
        "asset_type": state.get("asset_type", "stock"),
        "start_date": start_date,
        "end_date": end_date,
        "provider": state.get("provider", "auto"),
        "reasoning_summary": {
            **state.get("reasoning_summary", {}),
            "task_planner": task_plan.get("research_questions", []),
        },
        "warnings": warnings,
    }
