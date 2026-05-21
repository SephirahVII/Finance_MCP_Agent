from __future__ import annotations

from invesagent_agent.agents.base import run_llm_text_node
from invesagent_agent.prompts.report_writer import REPORT_WRITER_PROMPT
from invesagent_agent.workflows.research_state import ResearchState


def _format_metric(value, suffix: str = "") -> str:
    if value is None:
        return "N/A"
    if isinstance(value, float):
        return f"{value:.2f}{suffix}"
    return f"{value}{suffix}"


def _format_amount(value) -> str:
    if value is None:
        return "N/A"
    try:
        number = float(value)
    except (TypeError, ValueError):
        return str(value)
    if abs(number) >= 100_000_000:
        return f"{number / 100_000_000:.2f} 亿元"
    if abs(number) >= 10_000:
        return f"{number / 10_000:.2f} 万元"
    return f"{number:.2f} 元"


def _price_section(state: ResearchState) -> list[str]:
    lines = ["## 量价分析"]
    price = state.get("price_volume_analysis", {})
    raw = price.get("raw", price)
    analysis = price.get("analysis", {})
    single = raw.get("single_instrument", {})

    if analysis:
        lines.append(f"- 分析摘要: {analysis.get('summary', 'N/A')}")
        for finding in analysis.get("key_findings", [])[:5]:
            lines.append(f"- {finding}")

    if not single:
        return lines + ["暂无可用量价分析结果。"]

    for symbol, result in single.items():
        metrics = result.get("metrics") or {}
        lines.append(
            (
                f"- {symbol}: 区间收益率 {_format_metric(metrics.get('return_pct'), '%')}，"
                f"年化波动率 {_format_metric(metrics.get('annual_volatility_pct'), '%')}，"
                f"最大回撤 {_format_metric(metrics.get('max_drawdown_pct'), '%')}，"
                f"最新收盘价 {_format_metric(metrics.get('latest_close'))}。"
            )
        )

    comparison = raw.get("peer_comparison")
    if comparison and comparison.get("success"):
        rankings = comparison.get("rankings", {})
        lines.append(f"- 横向收益率排序: {', '.join(rankings.get('by_return', [])) or 'N/A'}")
        lines.append(f"- 横向低回撤排序: {', '.join(rankings.get('by_low_drawdown', [])) or 'N/A'}")

    return lines


def _fundamental_section(state: ResearchState) -> list[str]:
    lines = ["## 基本面分析"]
    fundamental_package = state.get("fundamental_analysis", {})
    fundamentals = fundamental_package.get("raw", fundamental_package)
    analysis = fundamental_package.get("analysis", {})

    if analysis:
        lines.append(f"- 分析摘要: {analysis.get('summary', 'N/A')}")
        for finding in analysis.get("key_findings", [])[:5]:
            lines.append(f"- {finding}")

    if not fundamentals:
        return lines + ["暂无可用基本面分析结果。"]

    for symbol, result in fundamentals.items():
        metrics = result.get("metrics") or {}
        if not result.get("success"):
            lines.append(f"- {symbol}: 基本面数据不可用，原因：{result.get('error_type') or result.get('message')}")
            continue
        lines.append(
            (
                f"- {symbol}: 最新营业收入 {_format_amount(metrics.get('latest_revenue'))}，"
                f"最新净利润 {_format_amount(metrics.get('latest_net_profit'))}，"
                f"经营现金流 {_format_amount(metrics.get('latest_operating_cashflow'))}，"
                f"ROE {_format_metric(metrics.get('latest_roe'), '%')}，"
                f"毛利率 {_format_metric(metrics.get('latest_gross_margin'), '%')}，"
                f"资产负债率 {_format_metric(metrics.get('debt_to_assets_pct'), '%')}。"
            )
        )

    return lines


def _industry_section(state: ResearchState) -> list[str]:
    lines = ["## 行业研究"]
    industry = state.get("industry_analysis", {})

    if industry.get("skipped"):
        return lines + ["本次任务未识别到明确行业，跳过行业研究模块。"]

    raw = industry.get("raw", industry)
    analysis = industry.get("analysis", {})
    if analysis:
        lines.append(f"- 分析摘要: {analysis.get('summary', 'N/A')}")
        for finding in analysis.get("key_findings", [])[:5]:
            lines.append(f"- {finding}")

    members = raw.get("members") or {}
    lines.append(f"- 行业: {raw.get('industry') or 'N/A'}")
    lines.append(f"- 行业股票池样本数量: {members.get('count') or len(members.get('members', []))}")

    sample = members.get("members", [])[:8]
    if sample:
        names = [f"{item.get('name')}({item.get('symbol')})" for item in sample]
        lines.append(f"- 样本公司: {', '.join(names)}")

    dynamics = raw.get("policy_and_dynamics", {})
    if dynamics:
        lines.append(f"- 政策与产业动态: {dynamics.get('message')}")

    return lines


def _chart_section(state: ResearchState) -> list[str]:
    lines = ["## 图表"]
    charts = state.get("charts", [])
    if not charts:
        return lines + ["暂无图表产物。"]

    for chart in charts:
        if chart.get("success"):
            lines.append(f"- {chart.get('symbol')}: {chart.get('relative_path') or chart.get('path')}")
        else:
            lines.append(f"- 图表生成失败: {chart.get('error_type') or chart.get('message')}")

    return lines


def _fallback_report(state: ResearchState, warnings: list[str]) -> str:
    plan = state.get("task_plan", {})
    lines = [
        "# 金融研究报告",
        "",
        "## 任务摘要",
        f"- 用户问题: {state.get('user_query', '')}",
        f"- 任务类型: {plan.get('task_type', 'N/A')}",
        f"- 分析区间: {state.get('start_date', 'N/A')} 至 {state.get('end_date', 'N/A')}",
        f"- 标的: {', '.join(state.get('symbols', [])) or 'N/A'}",
        f"- 行业: {state.get('industry') or 'N/A'}",
        "",
    ]

    for section in [
        _industry_section(state),
        _price_section(state),
        _fundamental_section(state),
        _chart_section(state),
    ]:
        lines.extend(section)
        lines.append("")

    reflection = state.get("reflection", {})
    if reflection:
        lines.append("## 审查意见")
        lines.append(f"- 状态: {reflection.get('status', 'N/A')}")
        lines.append(f"- 摘要: {reflection.get('summary', 'N/A')}")
        for issue in reflection.get("issues", [])[:10]:
            lines.append(f"- {issue}")
        lines.append("")

    lines.append("## 数据限制与风险提示")
    if warnings:
        for warning in warnings[:20]:
            lines.append(f"- {warning}")
    else:
        lines.append("- 未发现工具层返回的显著数据警告。")
    lines.append("- 本报告仅用于数据分析和研究学习，不构成投资建议。")

    return "\n".join(lines)


def run_report_writer(state: ResearchState) -> ResearchState:
    """Generate a Markdown research report from prior agent outputs."""
    warnings = list(state.get("warnings", []))
    fallback = _fallback_report(state, warnings)
    final_report = run_llm_text_node(
        system_prompt=REPORT_WRITER_PROMPT,
        context={
            "user_query": state.get("user_query", ""),
            "task_plan": state.get("task_plan", {}),
            "industry_analysis": state.get("industry_analysis", {}),
            "price_volume_analysis": state.get("price_volume_analysis", {}),
            "fundamental_analysis": state.get("fundamental_analysis", {}),
            "charts": state.get("charts", []),
            "reflection": state.get("reflection", {}),
            "warnings": warnings,
        },
        fallback=fallback,
        warnings=warnings,
    )
    return {
        **state,
        "draft_report": fallback,
        "final_report": final_report,
        "warnings": warnings,
    }
