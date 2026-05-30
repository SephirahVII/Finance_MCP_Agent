from __future__ import annotations

from typing import Any

from invesagent_agent.prompts.company_research_report import COMPANY_RESEARCH_REPORT_PROMPT
from invesagent_agent.prompts.report_writer import REPORT_WRITER_PROMPT
from invesagent_agent.reports import FinancialReportSkill
from invesagent_agent.runtime.agent_runtime import AgentRuntime
from invesagent_agent.workflows.research_state import ResearchState


def _first_symbol(state: ResearchState) -> str | None:
    symbols = state.get("symbols", [])
    return symbols[0] if symbols else None


def _instrument_name(state: ResearchState, symbol: str | None) -> str | None:
    for item in state.get("data_package", {}).get("instruments", []):
        if item.get("symbol") == symbol:
            return item.get("name") or item.get("symbol")
    return symbol


def _symbol_price_result(state: ResearchState, symbol: str | None) -> dict[str, Any]:
    if not symbol:
        return {}
    raw = state.get("price_volume_analysis", {}).get("raw", {})
    return raw.get("single_instrument", {}).get(symbol, {})


def _symbol_fundamental_result(state: ResearchState, symbol: str | None) -> dict[str, Any]:
    if not symbol:
        return {}
    raw = state.get("fundamental_analysis", {}).get("raw", {})
    return raw.get(symbol, {})


def _symbol_valuation_result(state: ResearchState, symbol: str | None) -> dict[str, Any]:
    if not symbol:
        return {}
    raw = state.get("valuation_analysis", {}).get("raw", {})
    return raw.get(symbol, {})


def _symbol_charts(state: ResearchState, symbol: str | None) -> list[dict[str, Any]]:
    charts = state.get("charts", [])
    if not symbol:
        return charts
    return [chart for chart in charts if chart.get("symbol") == symbol]


def _extract_price_metrics(price_result: dict[str, Any]) -> dict[str, Any]:
    metrics = price_result.get("metrics") or {}
    return {
        "latest_close": metrics.get("latest_close"),
        "first_close": metrics.get("first_close"),
        "return_pct": metrics.get("return_pct"),
        "annual_volatility_pct": metrics.get("annual_volatility_pct"),
        "max_drawdown_pct": metrics.get("max_drawdown_pct"),
        "highest_price": metrics.get("highest_price") or metrics.get("period_high"),
        "lowest_price": metrics.get("lowest_price") or metrics.get("period_low"),
        "ma5": metrics.get("ma5"),
        "ma20": metrics.get("ma20"),
        "ma60": metrics.get("ma60"),
        "avg_amount": metrics.get("avg_amount"),
        "record_count": price_result.get("count") or metrics.get("record_count"),
        "data_start": price_result.get("start_date"),
        "data_end": price_result.get("end_date"),
    }


def _extract_market_snapshot(state: ResearchState, symbol: str | None) -> dict[str, Any]:
    price_result = _symbol_price_result(state, symbol)
    valuation_result = _symbol_valuation_result(state, symbol)
    price_metrics = _extract_price_metrics(price_result)
    valuation_metrics = valuation_result.get("metrics") or {}

    snapshot = {
        "report_date": state.get("end_date"),
        "current_price": price_metrics.get("latest_close") or valuation_metrics.get("latest_close"),
        "one_year_high": price_metrics.get("highest_price"),
        "one_year_low": price_metrics.get("lowest_price"),
        "market_cap": valuation_metrics.get("latest_total_mv"),
        "float_market_cap": valuation_metrics.get("latest_circ_mv"),
        "total_shares": valuation_metrics.get("latest_total_share"),
        "float_shares": valuation_metrics.get("latest_float_share"),
        "latest_turnover_rate": valuation_metrics.get("latest_turnover_rate"),
        "three_month_turnover_rate": valuation_metrics.get("three_month_avg_turnover_rate"),
        "pe_ttm": valuation_metrics.get("latest_pe_ttm"),
        "pb": valuation_metrics.get("latest_pb"),
        "ps_ttm": valuation_metrics.get("latest_ps_ttm"),
        "data_limits": [],
    }

    if snapshot["current_price"] is None:
        snapshot["data_limits"].append("价格和估值数据中均未提供当前价格或最新收盘价。")
    if snapshot["one_year_high"] is None or snapshot["one_year_low"] is None:
        snapshot["data_limits"].append("价格指标中未提供区间最高价或最低价。")
    if valuation_result.get("success") is False:
        snapshot["data_limits"].append(
            "估值数据不可用："
            f"{valuation_result.get('error_type') or 'unknown'} - {valuation_result.get('message') or '无详细消息'}"
        )
    elif not valuation_result:
        snapshot["data_limits"].append("估值数据未被请求或未返回。")
    return snapshot


def _build_company_report_context(state: ResearchState) -> dict[str, Any]:
    symbol = _first_symbol(state)
    price_package = state.get("price_volume_analysis", {})
    valuation_package = state.get("valuation_analysis", {})
    fundamental_package = state.get("fundamental_analysis", {})
    industry_package = state.get("industry_analysis", {})
    price_result = _symbol_price_result(state, symbol)

    return {
        "report_type": _report_type(state, "company_research_report"),
        "user_query": state.get("user_query", ""),
        "task_plan": state.get("task_plan", {}),
        "report_review": state.get("report_review", {}),
        "company": {
            "name": _instrument_name(state, symbol),
            "symbol": symbol,
            "market": state.get("market", "cn"),
            "asset_type": state.get("asset_type", "stock"),
            "industry": state.get("industry"),
        },
        "scope": {
            "start_date": state.get("start_date"),
            "end_date": state.get("end_date"),
            "user_date_range": state.get("user_date_range", {}),
            "date_ranges": state.get("date_ranges", {}),
            "modules_executed": state.get("required_agents", []),
        },
        "market_snapshot": _extract_market_snapshot(state, symbol),
        "price_volume": {
            "metrics": _extract_price_metrics(price_result),
            "raw_result": price_result,
            "analysis": price_package.get("analysis", {}),
            "data_limits": price_package.get("analysis", {}).get("data_limits", []),
        },
        "valuation": {
            "raw_result": _symbol_valuation_result(state, symbol),
            "analysis": valuation_package.get("analysis", {}),
            "data_limits": valuation_package.get("analysis", {}).get("data_limits", []),
        },
        "fundamentals": {
            "raw_result": _symbol_fundamental_result(state, symbol),
            "analysis": fundamental_package.get("analysis", {}),
            "data_limits": fundamental_package.get("analysis", {}).get("data_limits", []),
        },
        "industry_background": {
            "raw_result": industry_package.get("raw", industry_package),
            "analysis": industry_package.get("analysis", {}),
            "data_limits": industry_package.get("analysis", {}).get("data_limits", []),
        },
        "macro_policy_analysis": state.get("macro_policy_analysis", {}),
        "charts": _symbol_charts(state, symbol),
        "warnings": list(state.get("warnings", [])),
        "data_sources": ["InvesAgent MCP 工具", "MCP 结果中注明的 Tushare / AKShare 数据"],
    }


def _build_generic_report_context(state: ResearchState, warnings: list[str]) -> dict[str, Any]:
    return {
        "report_type": _report_type(state, "generic_report"),
        "user_query": state.get("user_query", ""),
        "task_plan": state.get("task_plan", {}),
        "user_date_range": state.get("user_date_range", {}),
        "date_ranges": state.get("date_ranges", {}),
        "report_review": state.get("report_review", {}),
        "industry_analysis": state.get("industry_analysis", {}),
        "macro_policy_analysis": state.get("macro_policy_analysis", {}),
        "price_volume_analysis": state.get("price_volume_analysis", {}),
        "valuation_analysis": state.get("valuation_analysis", {}),
        "fundamental_analysis": state.get("fundamental_analysis", {}),
        "charts": state.get("charts", []),
        "reflection": state.get("reflection", {}),
        "warnings": warnings,
    }


def _should_use_company_report(state: ResearchState) -> bool:
    symbols = state.get("symbols", [])
    report_type = state.get("report_review", {}).get("report_type")
    if len(symbols) != 1:
        return False
    return report_type in {"stock_trend_report", "company_research_report"} or state.get("task_plan", {}).get(
        "task_type"
    ) in {"company_research", "full_report", "fundamental_analysis", "price_query"}


def _should_use_macro_policy_report(state: ResearchState) -> bool:
    return _report_type(state) == "macro_research_report" or state.get("task_plan", {}).get(
        "task_type"
    ) == "macro_research"


def _report_type(state: ResearchState, fallback: str = "generic_report") -> str:
    review_type = state.get("report_review", {}).get("report_type")
    plan_type = state.get("task_plan", {}).get("report_type")
    report_type = review_type or plan_type or fallback
    return "generic_report" if report_type in {None, "", "none", "analysis_summary"} else str(report_type)


def _fallback_report(context: dict[str, Any]) -> str:
    if context.get("report_type") == "macro_research_report":
        macro = context.get("macro_policy_analysis", {})
        analysis = macro.get("analysis", {}) if isinstance(macro, dict) else {}
        raw = macro.get("raw", {}) if isinstance(macro, dict) else {}
        lines = [
            "# Macro / Policy Research",
            "",
            f"- Report type: {context.get('report_type')}",
            f"- Query: {context.get('user_query')}",
            "",
            "## Summary",
            analysis.get("summary") or "Macro/policy retrieval completed.",
            "",
            "## Key Findings",
        ]
        for item in (analysis.get("key_findings") or [])[:8]:
            lines.append(f"- {item}")
        lines.extend(["", "## Retrieved Evidence"])
        for hit in (raw.get("hits") or [])[:8]:
            lines.append(
                f"- {hit.get('title') or hit.get('source_name')} "
                f"({hit.get('year')}, {hit.get('chunk_id')}): "
                f"{(hit.get('text') or '')[:180]}"
            )
        limits = [
            *(analysis.get("data_limits") or []),
            *context.get("warnings", []),
        ]
        if limits:
            lines.extend(["", "## Data Limits And Risks"])
            for item in limits[:12]:
                lines.append(f"- {item}")
        lines.append("\nThis report is for research only and is not investment advice.")
        return "\n".join(lines)

    review = context.get("report_review", {})
    company = context.get("company", {})
    snapshot = context.get("market_snapshot", {})
    price = context.get("price_volume", {})
    metrics = price.get("metrics", {})
    charts = context.get("charts", [])
    title = company.get("name") or company.get("symbol") or "研究对象"

    lines = [
        f"# {title} ({company.get('symbol') or 'N/A'})",
        "",
        f"- 报告类型：{context.get('report_type')}",
        f"- 数据区间：{context.get('scope', {}).get('start_date')} 至 {context.get('scope', {}).get('end_date')}",
        "",
        "## 关键市场数据",
        f"- 当前价格/最新收盘价：{snapshot.get('current_price')}",
        f"- 区间最高/最低：{snapshot.get('one_year_high')} / {snapshot.get('one_year_low')}",
        f"- 总市值/流通市值：{snapshot.get('market_cap')} / {snapshot.get('float_market_cap')}",
        f"- PE TTM / PB / PS TTM：{snapshot.get('pe_ttm')} / {snapshot.get('pb')} / {snapshot.get('ps_ttm')}",
        f"- 最新换手率/三个月平均换手率：{snapshot.get('latest_turnover_rate')} / {snapshot.get('three_month_turnover_rate')}",
        "",
        "## 股价表现与量价特征",
        f"- 区间收益率：{metrics.get('return_pct')}",
        f"- 年化波动率：{metrics.get('annual_volatility_pct')}",
        f"- 最大回撤：{metrics.get('max_drawdown_pct')}",
        f"- 摘要：{price.get('analysis', {}).get('summary')}",
        "",
    ]
    if context.get("report_type") == "company_research_report":
        lines.extend(
            [
                "## 财务与基本面",
                f"- {context.get('fundamentals', {}).get('analysis', {}).get('summary', '不可用')}",
                "",
                "## 公司与行业背景",
                f"- {context.get('industry_background', {}).get('analysis', {}).get('summary', '不可用')}",
                "",
            ]
        )
    if charts:
        lines.append("## 图表")
        for chart in charts:
            lines.append(f"- {chart.get('relative_path') or chart.get('path')}")
        lines.append("")

    limits = [
        *snapshot.get("data_limits", []),
        *review.get("missing_required_requirements", []),
        *review.get("failed_data", []),
    ]
    if limits:
        lines.append("## 数据限制与风险提示")
        for item in limits[:20]:
            lines.append(f"- {item}")
    lines.append("\n本报告仅用于研究和数据分析，不构成任何投资建议。")
    return "\n".join(lines)


def run_report_writer(state: ResearchState) -> ResearchState:
    """Generate a Markdown research report from prior agent outputs."""
    runtime = AgentRuntime(state, "report_writer")
    warnings = list(state.get("warnings", []))
    report_type = _report_type(state)
    skill = FinancialReportSkill()
    if _should_use_company_report(state) and not _should_use_macro_policy_report(state):
        report_context = _build_company_report_context(state)
    else:
        report_context = _build_generic_report_context(state, warnings)
    try:
        prompt = skill.load_prompt(report_type)
    except (FileNotFoundError, OSError):
        prompt = COMPANY_RESEARCH_REPORT_PROMPT if _should_use_company_report(state) else REPORT_WRITER_PROMPT

    fallback = _fallback_report(report_context)
    final_report = runtime.call_llm_text(
        system_prompt=prompt,
        context={"report_context": report_context},
        fallback=fallback,
    )
    return runtime.finish(
        {
            "report_context": report_context,
            "draft_report": fallback,
            "final_report": final_report,
            "final_response": final_report,
        }
    )
