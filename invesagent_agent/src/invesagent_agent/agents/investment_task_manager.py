from __future__ import annotations

import re
from datetime import date, timedelta
from typing import Any

from invesagent_agent.clients.tool_client import get_tool_client
from invesagent_agent.prompts.investment_task_manager import INVESTMENT_TASK_MANAGER_PROMPT
from invesagent_agent.runtime.agent_runtime import AgentRuntime
from invesagent_agent.workflows.research_state import ResearchState


_TS_CODE_RE = re.compile(r"\b\d{6}\.(?:SH|SZ|BJ)\b", re.IGNORECASE)
_DATE_RE = re.compile(r"\d{4}[-/]?\d{2}[-/]?\d{2}")
_YEAR_RE = re.compile(r"(?<!\d)(20\d{2})(?:\s*年)?(?!\d)")
_PRICE_TERMS = {"价格", "股价", "行情", "走势", "趋势", "量价", "技术", "K线", "k线", "回撤", "波动", "图表"}
_FUNDAMENTAL_TERMS = {"基本面", "财务", "利润", "营收", "现金流", "ROE", "毛利率", "资产负债"}
_VALUATION_TERMS = {"估值", "市值", "换手率", "PE", "PB", "PS", "股本", "流通市值"}
_INDUSTRY_TERMS = {"行业", "产业", "股票池", "成分股", "同行", "可比公司"}
_NEWS_TERMS = {
    "新闻",
    "资讯",
    "舆情",
    "公告",
    "事件",
    "热点",
    "催化",
    "消息",
    "利好",
    "利空",
    "负面",
    "研报",
    "研究报告",
    "发生了什么",
    "市场关注",
}
_REPORT_TERMS = {"报告", "研报", "完整分析", "完整研究"}
_MACRO_POLICY_TERMS = {
    "macro",
    "policy",
    "liquidity",
    "inflation",
    "pmi",
    "宏观",
    "政策",
    "财政",
    "货币",
    "流动性",
    "利率",
    "通胀",
    "稳增长",
    "扩内需",
}
_DATE_MODULES = ("price_volume", "valuation", "fundamentals", "industry", "macro_policy", "news")
_REPORT_TYPES = {
    "none",
    "stock_trend_report",
    "company_research_report",
    "industry_research_report",
    "macro_research_report",
    "company_valuation_report",
    "stock_investment_recommendation_report",
    "generic_report",
}


def _normalize_date(value: str) -> str:
    return value.replace("-", "").replace("/", "")


def _extract_dates(query: str) -> tuple[str | None, str | None]:
    matches = [_normalize_date(item) for item in _DATE_RE.findall(query)]
    if len(matches) >= 2:
        return matches[0], matches[1]
    years = _YEAR_RE.findall(query)
    if years:
        year = years[0]
        return f"{year}0101", f"{year}1231"
    return None, None


def _user_date_range(query: str) -> dict[str, Any]:
    start_date, end_date = _extract_dates(query)
    return {
        "start_date": start_date,
        "end_date": end_date,
        "explicit": bool(start_date and end_date),
    }


def _default_dates() -> tuple[str, str]:
    current_year = date.today().year
    return f"{current_year - 1}0101", f"{current_year}1231"


def _format_date(value: date) -> str:
    return value.strftime("%Y%m%d")


def _default_date_ranges(
    required_agents: list[str],
    start_date: str | None,
    end_date: str | None,
) -> dict[str, dict[str, str]]:
    """Build module-level default ranges while preserving explicit user dates."""
    modules = _modules_from_agents(required_agents)
    if start_date and end_date:
        explicit_range = {"start_date": start_date, "end_date": end_date}
        return {
            module: dict(explicit_range)
            for module in _DATE_MODULES
            if modules.get(module)
        }

    today = date.today()
    ranges = {
        "price_volume": {
            "start_date": _format_date(today - timedelta(days=90)),
            "end_date": _format_date(today),
        },
        "macro_policy": {
            "start_date": f"{today.year - 5}0101",
            "end_date": _format_date(today),
        },
        "valuation": {
            "start_date": _format_date(today - timedelta(days=365)),
            "end_date": _format_date(today),
        },
        "fundamentals": {
            "start_date": _format_date(today - timedelta(days=365)),
            "end_date": _format_date(today),
        },
        "industry": {
            "start_date": _format_date(today - timedelta(days=90)),
            "end_date": _format_date(today),
        },
        "news": {
            "start_date": _format_date(today - timedelta(days=30)),
            "end_date": _format_date(today),
        },
    }
    return {
        module: range_value
        for module, range_value in ranges.items()
        if modules.get(module)
    }


def _extract_symbols(query: str) -> list[str]:
    return list(dict.fromkeys(item.upper() for item in _TS_CODE_RE.findall(query)))


def _contains_any(query: str, terms: set[str]) -> bool:
    lower = query.lower()
    return any(term.lower() in lower for term in terms)


def _extract_industry(query: str, market: str, provider: str, tool_client=None) -> str | None:
    try:
        result = get_tool_client(tool_client).call_tool(
            "list_industries_tool",
            {"market": market, "provider": provider},
        )
        industries = result.get("industries", []) if result.get("success") else []
    except Exception:
        industries = []

    matches = [industry for industry in industries if industry and industry in query]
    if matches:
        return sorted(matches, key=len, reverse=True)[0]
    return None


def _try_resolve_symbol(query: str, tool_client=None) -> list[str]:
    try:
        resolved = get_tool_client(tool_client).call_tool("resolve_instrument_tool", {"query": query})
    except Exception:
        return []
    symbol = resolved.get("symbol")
    market = resolved.get("market")
    if symbol and market != "unknown":
        return [symbol]
    return []


def _heuristic_plan(state: ResearchState) -> dict[str, Any]:
    """Build a minimal factual fallback; the prompt decides the semantic route."""
    query = state["user_query"].strip()
    market = state.get("market", "cn")
    asset_type = state.get("asset_type", "stock")
    provider = state.get("provider", "auto")
    user_date_range = _user_date_range(query)
    symbols = _extract_symbols(query)
    tool_client = state.get("tool_client")
    industry = _extract_industry(query, market, provider, tool_client=tool_client)
    start_date = user_date_range.get("start_date")
    end_date = user_date_range.get("end_date")

    if not symbols and not industry and _contains_any(query, _MACRO_POLICY_TERMS):
        wants_report = _contains_any(query, _REPORT_TERMS)
        required_agents = ["macro_policy_analyst"]
        if wants_report:
            required_agents.extend(["reviewer", "report_writer"])
        return {
            "action": "execute",
            "task_type": "macro_research",
            "target": {
                "symbols": [],
                "names": [],
                "industry": None,
                "market": market,
                "asset_type": asset_type,
            },
            "start_date": start_date,
            "end_date": end_date,
            "user_date_range": user_date_range,
            "date_ranges": _default_date_ranges(required_agents, start_date, end_date),
            "required_agents": required_agents,
            "modules": _modules_from_agents(required_agents),
            "agent_tasks": {
                "macro_policy_analyst": "使用 RagRetriever 检索并分析宏观/政策证据。",
                "report_writer": "基于检索证据生成宏观/政策研究报告。",
            },
            "tool_needs": {"macro_policy_analyst": ["RagRetriever.retrieve_policy"]},
            "needs_tool": True,
            "needs_clarification": False,
            "missing_fields": [],
            "clarifying_question": None,
            "direct_answer": None,
            "output_type": "full_report" if wants_report else "analysis_summary",
            "report_type": "macro_research_report" if wants_report else "none",
            "report_requirements": {
                "language": "zh-CN",
                "style": "专业、克制、证据可追溯",
                "length": "根据任务复杂度决定",
            },
            "reason": "识别到宏观/政策问题，交给基于 RagRetriever 的宏观政策分析 Agent。",
        }

    if not symbols and query:
        symbols = _try_resolve_symbol(query, tool_client=tool_client)

    if not symbols and not industry:
        return {
            "action": "clarification",
            "task_type": "ambiguous_investment_task",
            "target": {
                "symbols": [],
                "names": [],
                "industry": None,
                "market": market,
                "asset_type": asset_type,
            },
            "start_date": start_date,
            "end_date": end_date,
            "user_date_range": user_date_range,
            "date_ranges": {},
            "required_agents": [],
            "agent_tasks": {},
            "tool_needs": {},
            "needs_tool": False,
            "needs_clarification": True,
            "missing_fields": ["target"],
            "clarifying_question": "请补充你要研究的具体公司、股票代码、指数或行业，以及希望重点分析什么。",
            "direct_answer": None,
            "output_type": "brief_answer",
            "report_requirements": {"language": "zh-CN", "style": "专业", "length": "按任务需要"},
            "reason": "缺少明确研究对象。",
        }

    return {
        "action": "execute",
        "task_type": "investment_task",
        "target": {
            "symbols": symbols,
            "names": [],
            "industry": industry,
            "market": market,
            "asset_type": asset_type,
        },
        "start_date": start_date,
        "end_date": end_date,
        "user_date_range": user_date_range,
        "date_ranges": {},
        "required_agents": ["data_collector"],
        "modules": {"data": True},
        "agent_tasks": {
            "data_collector": "解析研究对象，准备后续专业 Agent 所需的标的、行业和基础数据。"
        },
        "tool_needs": {
            "data_collector": ["resolve_instrument_tool", "get_industry_members_tool"]
        },
        "needs_tool": True,
        "needs_clarification": False,
        "missing_fields": [],
        "clarifying_question": None,
        "direct_answer": None,
        "output_type": "analysis_summary",
        "report_requirements": {
            "language": "zh-CN",
            "style": "专业、克制、可审计",
            "length": "根据用户任务复杂度决定",
        },
        "reason": "已解析研究对象和显式时间范围；具体任务类型和 Agent 分派由 LLM task manager 判断。",
    }


def _normalize_required_agents(value: Any) -> list[str]:
    allowed = {
        "data_collector",
        "news_analyst",
        "macro_policy_analyst",
        "industry_analyst",
        "price_volume_analyst",
        "valuation_analyst",
        "fundamental_analyst",
        "reviewer",
        "report_writer",
    }
    if not isinstance(value, list):
        return []
    return [str(item) for item in value if str(item) in allowed]


def _modules_from_agents(required_agents: list[str]) -> dict[str, bool]:
    return {
        "data": "data_collector" in required_agents,
        "news": "news_analyst" in required_agents,
        "macro_policy": "macro_policy_analyst" in required_agents,
        "industry": "industry_analyst" in required_agents,
        "price_volume": "price_volume_analyst" in required_agents,
        "valuation": "valuation_analyst" in required_agents,
        "fundamentals": "fundamental_analyst" in required_agents,
        "review": "reviewer" in required_agents,
        "report": "report_writer" in required_agents,
    }


def _agents_from_modules(modules: Any) -> list[str]:
    module_to_agent = {
        "data": "data_collector",
        "news": "news_analyst",
        "macro_policy": "macro_policy_analyst",
        "industry": "industry_analyst",
        "price_volume": "price_volume_analyst",
        "valuation": "valuation_analyst",
        "fundamentals": "fundamental_analyst",
        "review": "reviewer",
        "report": "report_writer",
    }
    selected: list[str] = []
    if isinstance(modules, dict):
        for module, enabled in modules.items():
            if enabled and module in module_to_agent:
                selected.append(module_to_agent[module])
    elif isinstance(modules, list):
        for module in modules:
            if module in module_to_agent:
                selected.append(module_to_agent[module])
    return list(dict.fromkeys(selected))


def _normalize_plan_date_ranges(
    value: Any,
    required_agents: list[str],
    fallback_ranges: dict[str, dict[str, str]],
) -> dict[str, dict[str, str]]:
    modules = _modules_from_agents(required_agents)
    normalized = {module: dict(range_value) for module, range_value in fallback_ranges.items()}
    if not isinstance(value, dict):
        return normalized

    for module in _DATE_MODULES:
        if module not in value or not modules.get(module):
            continue
        item = value.get(module)
        if not isinstance(item, dict):
            continue
        start_date = item.get("start_date") or item.get("start")
        end_date = item.get("end_date") or item.get("end")
        if isinstance(start_date, str) and isinstance(end_date, str):
            start_date = _normalize_date(start_date)
            end_date = _normalize_date(end_date)
            if re.fullmatch(r"\d{8}", start_date) and re.fullmatch(r"\d{8}", end_date):
                normalized[module] = {
                    "start_date": start_date,
                    "end_date": end_date,
                }
    return normalized


def _normalize_report_type(value: Any, output_type: str | None) -> str:
    report_type = str(value or "none").strip()
    if report_type not in _REPORT_TYPES:
        report_type = "none"
    if output_type != "full_report":
        return "none"
    return "generic_report" if report_type == "none" else report_type


def run_investment_task_manager(state: ResearchState) -> ResearchState:
    """Plan investment research tasks and decide which specialist agents should run."""
    runtime = AgentRuntime(state, "investment_task_manager")
    fallback = _heuristic_plan(state)
    explicit_user_range = _user_date_range(state.get("user_query", ""))
    llm_plan = runtime.call_llm_json(
        system_prompt=INVESTMENT_TASK_MANAGER_PROMPT,
        context={
            "latest_user_input": state.get("user_query", ""),
            "recent_messages_for_context": state.get("messages", [])[-6:],
            "task_memory_for_this_session": state.get("task_memory", {}),
            "heuristic_plan": fallback,
            "user_date_range": explicit_user_range,
            "current_date": _format_date(date.today()),
            "planner_contract": {
                "prefer_semantic_judgment_over_keywords": True,
                "decide_needs_tools_before_selecting_agents": True,
                "use_module_date_ranges": True,
                "default_policy": {
                    "price_volume": "最近3个月，除非用户指定时间",
                    "industry": "最近3个月，除非用户指定时间",
                    "fundamentals": "最近1年，除非用户指定时间",
                    "valuation": "最近1年，除非用户指定时间",
                },
            },
            "market": state.get("market", "cn"),
            "asset_type": state.get("asset_type", "stock"),
            "provider": state.get("provider", "auto"),
        },
        fallback=fallback,
        task=(
            "请生成投资研究任务计划。不要做指标计算，只做任务理解、信息完整性判断、"
            "时间口径确认和 Agent 分派。若用户只是询问股价走势、股票趋势、价格表现，"
            "请优先选择 analysis_summary，并自行判断是否真的需要 report_writer。"
        ),
    )

    plan = {**fallback, **{key: value for key, value in llm_plan.items() if value is not None}}
    action = plan.get("action") or fallback["action"]
    if action not in {"direct_answer", "clarification", "execute"}:
        action = fallback["action"]
    plan["action"] = action

    target = plan.get("target") if isinstance(plan.get("target"), dict) else fallback["target"]
    symbols = [str(symbol).upper() for symbol in target.get("symbols", []) if symbol]
    if not symbols:
        symbols = fallback.get("target", {}).get("symbols", [])
    industry = target.get("industry") or fallback["target"].get("industry")
    required_agents = _normalize_required_agents(plan.get("required_agents"))
    module_agents = _agents_from_modules(plan.get("modules"))
    if module_agents:
        required_agents = list(dict.fromkeys([*module_agents, *required_agents]))
    if action == "execute" and not required_agents:
        required_agents = fallback.get("required_agents", [])
    plan["required_agents"] = required_agents
    plan["modules"] = _modules_from_agents(required_agents)
    plan["target"] = {**fallback["target"], **target, "symbols": symbols, "industry": industry}
    plan["report_type"] = _normalize_report_type(plan.get("report_type"), plan.get("output_type"))
    wants_news = (
        _contains_any(state.get("user_query", ""), _NEWS_TERMS)
        or plan.get("task_type") in {"company_research", "industry_research"}
        or plan.get("report_type") in {"company_research_report", "industry_research_report"}
    )
    if action == "execute" and wants_news and (symbols or industry):
        required_agents = list(dict.fromkeys(["data_collector", *required_agents, "news_analyst"]))
        plan["required_agents"] = required_agents
        plan["modules"] = _modules_from_agents(required_agents)

    fallback_date_ranges = fallback.get("date_ranges", {})
    if not isinstance(fallback_date_ranges, dict) or not fallback_date_ranges:
        user_start_date, user_end_date = _extract_dates(state.get("user_query", ""))
        fallback_date_ranges = _default_date_ranges(required_agents, user_start_date, user_end_date)
    date_ranges = _normalize_plan_date_ranges(
        plan.get("date_ranges"),
        required_agents,
        fallback_date_ranges,
    )
    if explicit_user_range["explicit"]:
        user_range = {
            "start_date": explicit_user_range["start_date"],
            "end_date": explicit_user_range["end_date"],
        }
        date_ranges = {
            module: dict(user_range)
            for module, enabled in _modules_from_agents(required_agents).items()
            if enabled and module in _DATE_MODULES
        }
    if date_ranges:
        plan["start_date"] = min(item["start_date"] for item in date_ranges.values())
        plan["end_date"] = max(item["end_date"] for item in date_ranges.values())
    plan["date_ranges"] = date_ranges
    plan["user_date_range"] = explicit_user_range

    final_response = None
    if action == "direct_answer":
        final_response = plan.get("direct_answer") or "这个问题不需要调用投资数据工具，我可以直接回答。"
    elif action == "clarification":
        final_response = plan.get("clarifying_question") or "请补充研究对象、时间范围和分析重点。"

    return runtime.finish({
        "task_plan": plan,
        "symbols": symbols,
        "industry": industry,
        "market": target.get("market") or state.get("market", "cn"),
        "asset_type": target.get("asset_type") or state.get("asset_type", "stock"),
        "start_date": plan.get("start_date") or fallback.get("start_date"),
        "end_date": plan.get("end_date") or fallback.get("end_date"),
        "date_ranges": date_ranges,
        "user_date_range": explicit_user_range,
        "provider": state.get("provider", "auto"),
        "required_agents": required_agents,
        "final_response": final_response,
        "final_report": final_response or state.get("final_report", ""),
        "reasoning_summary": {
            **state.get("reasoning_summary", {}),
            "investment_task_manager": {
                "action": action,
                "required_agents": required_agents,
                "report_type": plan.get("report_type"),
                "reason": plan.get("reason"),
            },
        },
    })


def _has_successful_package(state: ResearchState, key: str) -> bool:
    package = state.get(key, {})
    raw = package.get("raw", package) if isinstance(package, dict) else {}
    if not isinstance(raw, dict):
        return False
    for value in raw.values():
        if isinstance(value, dict) and value.get("success"):
            return True
    single = raw.get("single_instrument") if isinstance(raw.get("single_instrument"), dict) else {}
    return any(isinstance(value, dict) and value.get("success") for value in single.values())


def run_investment_task_reviewer(state: ResearchState) -> ResearchState:
    """Review collected data before report writing and decide whether to retry modules."""
    runtime = AgentRuntime(state, "investment_task_reviewer")
    plan = state.get("task_plan", {})
    query = state.get("user_query", "")
    required_agents = list(state.get("required_agents", []))
    review_round = int(state.get("review_round", 0) or 0)
    warnings = list(state.get("warnings", []))

    planned_report_type = plan.get("report_type")
    wants_report = _contains_any(query, _REPORT_TERMS) or "report_writer" in required_agents
    wants_price = _contains_any(query, _PRICE_TERMS) or plan.get("task_type") in {
        "price_query",
        "price_volume_analysis",
    }
    wants_fundamental = _contains_any(query, _FUNDAMENTAL_TERMS)
    wants_valuation = _contains_any(query, _VALUATION_TERMS) or wants_report
    wants_industry = _contains_any(query, _INDUSTRY_TERMS) or bool(state.get("industry"))
    wants_news = (
        _contains_any(query, _NEWS_TERMS)
        or "news_analyst" in required_agents
        or planned_report_type in {"company_research_report", "industry_research_report"}
    )
    wants_macro_policy = (
        _contains_any(query, _MACRO_POLICY_TERMS)
        or plan.get("task_type") == "macro_research"
        or planned_report_type == "macro_research_report"
        or "macro_policy_analyst" in required_agents
    )

    if planned_report_type in _REPORT_TYPES and planned_report_type != "none":
        report_type = planned_report_type
    elif wants_report and wants_price and not (wants_fundamental or wants_industry):
        report_type = "stock_trend_report"
    elif wants_macro_policy:
        report_type = "macro_research_report" if wants_report else "analysis_summary"
    elif wants_industry and not state.get("symbols"):
        report_type = "industry_research_report"
    elif wants_report:
        report_type = "company_research_report"
    else:
        report_type = "analysis_summary"

    requirements = {
        "news": wants_news and not wants_macro_policy,
        "price_volume": (wants_price or wants_report) and not wants_macro_policy,
        "valuation": wants_valuation and not wants_macro_policy,
        "fundamentals": (wants_fundamental or report_type == "company_research_report")
        and not wants_macro_policy,
        "industry": wants_industry and not wants_macro_policy,
        "macro_policy": wants_macro_policy,
    }
    available = {
        "news": bool(state.get("news_analysis", {}).get("analysis")),
        "price_volume": _has_successful_package(state, "price_volume_analysis"),
        "valuation": _has_successful_package(state, "valuation_analysis"),
        "fundamentals": _has_successful_package(state, "fundamental_analysis"),
        "industry": bool(state.get("industry_analysis")),
        "macro_policy": bool(state.get("macro_policy_analysis", {}).get("raw", {}).get("hits")),
    }

    module_to_agent = {
        "news": "news_analyst",
        "price_volume": "price_volume_analyst",
        "valuation": "valuation_analyst",
        "fundamentals": "fundamental_analyst",
        "industry": "industry_analyst",
        "macro_policy": "macro_policy_analyst",
    }
    retry_agents = []
    missing_required = []
    missing_optional = []
    for module, required in requirements.items():
        if available.get(module):
            continue
        item = {
            "module": module,
            "agent": module_to_agent[module],
            "reason": "required by user request or selected report type",
            "can_retry": review_round < 1,
        }
        if required:
            missing_required.append(item)
            if review_round < 1:
                retry_agents.append(module_to_agent[module])
        else:
            missing_optional.append(item)

    retry_agents = list(dict.fromkeys(retry_agents))
    if retry_agents:
        required_agents = list(dict.fromkeys([*required_agents, *retry_agents]))
    user_start_date, user_end_date = _extract_dates(query)
    existing_date_ranges = state.get("date_ranges", {})
    if not isinstance(existing_date_ranges, dict):
        existing_date_ranges = {}
    date_ranges = {
        **_default_date_ranges(required_agents, user_start_date, user_end_date),
        **existing_date_ranges,
    }

    failed_data = []
    for package_name in ("valuation_analysis", "fundamental_analysis", "price_volume_analysis"):
        package = state.get(package_name, {})
        raw = package.get("raw", package) if isinstance(package, dict) else {}
        if not isinstance(raw, dict):
            continue
        for symbol, result in raw.items():
            if isinstance(result, dict) and result.get("success") is False:
                failed_data.append(
                    {
                        "module": package_name,
                        "symbol": symbol,
                        "error_type": result.get("error_type"),
                        "message": result.get("message"),
                    }
                )

    report_review = {
        "review_stage": "before_report",
        "report_type": report_type,
        "needs_report_writer": wants_report or report_type != "analysis_summary",
        "can_answer_user_request": not missing_required or review_round >= 1,
        "requirements": requirements,
        "available_data": available,
        "missing_required_requirements": missing_required,
        "missing_optional_requirements": missing_optional,
        "retry_agents": retry_agents,
        "failed_data": failed_data,
        "final_output_mode": "report" if wants_report or report_type != "analysis_summary" else "summary",
    }

    state["warnings"] = warnings
    return runtime.finish({
        "required_agents": required_agents,
        "date_ranges": date_ranges,
        "report_review": report_review,
        "review_round": review_round + 1,
    })
