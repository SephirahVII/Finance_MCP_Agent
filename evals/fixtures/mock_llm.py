from __future__ import annotations

import re
from datetime import date, timedelta
from typing import Any


_TS_CODE_RE = re.compile(r"\b\d{6}\.(?:SH|SZ|BJ)\b", re.IGNORECASE)
_DATE_RE = re.compile(r"\d{4}[-/]?\d{2}[-/]?\d{2}")


def install_mock_llm() -> None:
    """Patch AgentRuntime LLM calls with deterministic eval responses."""
    from invesagent_agent.runtime.agent_runtime import AgentRuntime

    AgentRuntime.call_llm_json = _mock_call_llm_json  # type: ignore[method-assign]
    AgentRuntime.call_llm_text = _mock_call_llm_text  # type: ignore[method-assign]


def _mock_call_llm_json(
    self,
    *,
    system_prompt: str,
    context: dict[str, Any],
    fallback: dict[str, Any],
    task: str = "",
) -> dict[str, Any]:
    del system_prompt, task
    if self.agent_name == "general_assistant":
        query = str(context.get("latest_user_input") or "")
        return _route_decision(query)
    if self.agent_name == "investment_task_manager":
        query = str(context.get("latest_user_input") or self.state.get("user_query") or "")
        return _task_plan(query, self.state, fallback)
    if self.agent_name == "investment_task_reviewer":
        return {"summary": "mock review", "retry_agents": [], "needs_report_writer": True}
    return {
        "summary": f"mock {self.agent_name} summary",
        "key_findings": [f"mock finding from {self.agent_name}"],
        "strengths": [],
        "risks": ["mock risk"],
        "data_limits": ["mock data limit"],
        "confidence": "medium",
        "reasoning_summary": [f"mock reasoning from {self.agent_name}"],
    }


def _mock_call_llm_text(
    self,
    *,
    system_prompt: str,
    context: dict[str, Any],
    fallback: str,
    task: str = "",
) -> str:
    del system_prompt, context, fallback, task
    if self.agent_name == "report_writer":
        return (
            "mock report: valuation, fundamentals, policy evidence, risks, "
            "data limits, and no investment advice."
        )
    return f"mock text response from {self.agent_name}"


def _route_decision(query: str) -> dict[str, Any]:
    text = query.lower()
    is_general = (
        "hello" in text
        or "what can you do" in text
        or "what is dcf" in text
        or "dcf?" in text
    )
    if is_general and not any(term in text for term in ("analyze", "generate", "report for")):
        return {
            "route": "general_answer",
            "intent": "general_or_concept",
            "needs_investment_workflow": False,
            "confidence": 0.95,
            "reason": "deterministic eval route",
            "response": "mock general answer",
            "normalized_query": query,
        }
    return {
        "route": "investment_task",
        "intent": "investment_research",
        "needs_investment_workflow": True,
        "confidence": 0.95,
        "reason": "deterministic eval route",
        "response": None,
        "normalized_query": query,
    }


def _task_plan(query: str, state: dict[str, Any], fallback: dict[str, Any]) -> dict[str, Any]:
    text = query.lower()
    symbols = _symbols(query)
    start_date, end_date = _dates(query)
    market = state.get("market", "cn")
    asset_type = state.get("asset_type", "stock")
    provider = state.get("provider", "auto")
    del provider

    if "fiscal policy" in text or "macro" in text or "domestic demand" in text:
        wants_report = "report" in text
        agents = ["macro_policy_analyst"]
        if wants_report:
            agents += ["reviewer", "report_writer"]
        return _plan(
            task_type="macro_research",
            symbols=[],
            industry=None,
            required_agents=agents,
            start_date=start_date,
            end_date=end_date,
            market=market,
            asset_type=asset_type,
            output_type="full_report" if wants_report else "analysis_summary",
            report_type="macro_research_report" if wants_report else "none",
        )

    if "liquor industry" in text:
        return _plan(
            task_type="industry_research",
            symbols=symbols,
            industry="liquor",
            required_agents=["data_collector", "industry_analyst"],
            start_date=start_date,
            end_date=end_date,
            market=market,
            asset_type=asset_type,
        )

    if "valuation" in text or "pe" in text or "pb" in text:
        wants_report = "report" in text
        agents = ["data_collector", "valuation_analyst"]
        if wants_report:
            agents += ["reviewer", "report_writer"]
        return _plan(
            task_type="valuation_analysis",
            symbols=symbols,
            industry=None,
            required_agents=agents,
            start_date=start_date,
            end_date=end_date,
            market=market,
            asset_type=asset_type,
            output_type="full_report" if wants_report else "analysis_summary",
            report_type="company_valuation_report" if wants_report else "none",
        )

    if any(term in text for term in ("fundamental", "revenue", "profit", "roe", "cash flow")):
        return _plan(
            task_type="fundamental_analysis",
            symbols=symbols,
            industry=None,
            required_agents=["data_collector", "fundamental_analyst"],
            start_date=start_date,
            end_date=end_date,
            market=market,
            asset_type=asset_type,
        )

    if "company research report" in text or (
        _TS_CODE_RE.fullmatch(query.strip()) and _memory_wants_report(state)
    ):
        return _plan(
            task_type="company_research_report",
            symbols=symbols or ["600519.SH"],
            industry=None,
            required_agents=["data_collector", "reviewer", "report_writer"],
            start_date=start_date,
            end_date=end_date,
            market=market,
            asset_type=asset_type,
            output_type="full_report",
            report_type="company_research_report",
        )

    if any(term in text for term in ("price", "trend", "volatility")):
        return _plan(
            task_type="price_volume_analysis",
            symbols=symbols,
            industry=None,
            required_agents=["data_collector", "price_volume_analyst"],
            start_date=start_date,
            end_date=end_date,
            market=market,
            asset_type=asset_type,
        )

    return fallback


def _symbols(query: str) -> list[str]:
    symbols = [item.upper() for item in _TS_CODE_RE.findall(query)]
    return list(dict.fromkeys(symbols))


def _dates(query: str) -> tuple[str | None, str | None]:
    dates = [item.replace("-", "").replace("/", "") for item in _DATE_RE.findall(query)]
    if len(dates) >= 2:
        return dates[0], dates[1]
    today = date.today()
    return (today - timedelta(days=90)).strftime("%Y%m%d"), today.strftime("%Y%m%d")


def _memory_wants_report(state: dict[str, Any]) -> bool:
    memory = state.get("task_memory", {})
    session = memory.get("session", {}) if isinstance(memory, dict) else {}
    last_query = str(session.get("last_query") or "").lower()
    return "report" in last_query


def _plan(
    *,
    task_type: str,
    symbols: list[str],
    industry: str | None,
    required_agents: list[str],
    start_date: str | None,
    end_date: str | None,
    market: str,
    asset_type: str,
    output_type: str = "analysis_summary",
    report_type: str = "none",
) -> dict[str, Any]:
    modules = _modules_from_agents(required_agents)
    date_ranges = {
        module: {"start_date": start_date, "end_date": end_date}
        for module in ("price_volume", "valuation", "fundamentals", "industry", "macro_policy")
        if modules.get(module) and start_date and end_date
    }
    return {
        "action": "execute",
        "task_type": task_type,
        "target": {
            "symbols": symbols,
            "names": [],
            "industry": industry,
            "market": market,
            "asset_type": asset_type,
        },
        "start_date": start_date,
        "end_date": end_date,
        "user_date_range": {
            "start_date": start_date,
            "end_date": end_date,
            "explicit": bool(start_date and end_date),
        },
        "date_ranges": date_ranges,
        "required_agents": required_agents,
        "modules": modules,
        "agent_tasks": {agent: f"Run {agent}" for agent in required_agents},
        "tool_needs": {},
        "needs_tool": True,
        "needs_clarification": False,
        "missing_fields": [],
        "clarifying_question": None,
        "direct_answer": None,
        "output_type": output_type,
        "report_type": report_type,
        "report_requirements": {"language": "en", "style": "concise"},
        "reason": "deterministic eval plan",
    }


def _modules_from_agents(required_agents: list[str]) -> dict[str, bool]:
    return {
        "data": "data_collector" in required_agents,
        "macro_policy": "macro_policy_analyst" in required_agents,
        "industry": "industry_analyst" in required_agents,
        "price_volume": "price_volume_analyst" in required_agents,
        "valuation": "valuation_analyst" in required_agents,
        "fundamentals": "fundamental_analyst" in required_agents,
        "review": "reviewer" in required_agents,
        "report": "report_writer" in required_agents,
    }

