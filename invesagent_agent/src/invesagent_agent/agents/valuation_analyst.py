from __future__ import annotations

from invesagent_agent.agents.base import (
    default_analysis,
    get_module_date_range,
    run_llm_json_node,
    run_mcp_tool_node,
)
from invesagent_agent.prompts.valuation_analyst import VALUATION_ANALYST_PROMPT
from invesagent_agent.workflows.research_state import ResearchState


def run_valuation_analyst(state: ResearchState) -> ResearchState:
    """Analyze valuation, market-value, and turnover metrics through MCP."""
    warnings = list(state.get("warnings", []))
    tool_calls = list(state.get("tool_calls", []))
    observations = list(state.get("observations", []))
    valuation = {}
    start_date, end_date = get_module_date_range(state, "valuation")
    date_range = {"start_date": start_date, "end_date": end_date}

    if not start_date or not end_date:
        message = "估值分析需要明确的开始日期和结束日期。"
        warnings.append("valuation_analyst skipped: missing start_date or end_date")
        return {
            **state,
            "valuation_analysis": {
                "raw": {},
                "date_range": date_range,
                "analysis": default_analysis(
                    summary=message,
                    data_limits=["缺少 start_date 或 end_date，未调用估值 MCP 工具。"],
                ),
            },
            "warnings": warnings,
        }

    for symbol in state.get("symbols", [])[:5]:
        result = run_mcp_tool_node(
            node="valuation_analyst",
            tool="analyze_valuation_tool",
            arguments={
                "symbol": symbol,
                "market": state.get("market", "cn"),
                "asset_type": state.get("asset_type", "stock"),
                "start_date": start_date,
                "end_date": end_date,
                "provider": state.get("provider", "auto"),
            },
            tool_calls=tool_calls,
            observations=observations,
            warnings=warnings,
            observation={"symbol": symbol},
            state=state,
        )
        valuation[symbol] = result
        if result.get("message"):
            warnings.append(f"{symbol}: valuation {result.get('error_type') or 'warning'} - {result.get('message')}")
        warnings.extend([f"{symbol}: {warning}" for warning in result.get("warnings", [])])
        if observations:
            observations[-1]["error_type"] = result.get("error_type")

    analysis = run_llm_json_node(
        system_prompt=VALUATION_ANALYST_PROMPT,
        context={
            "user_query": state.get("user_query"),
            "task_plan": state.get("task_plan", {}),
            "date_range": date_range,
            "user_date_range": state.get("user_date_range", {}),
            "raw": valuation,
        },
        fallback=default_analysis(
            summary="估值 MCP 工具已完成调用，但 LLM 解读不可用。",
            key_findings=[f"已处理 {len(valuation)} 个标的的估值分析。"],
            data_limits=warnings[-5:],
        ),
        warnings=warnings,
        role="valuation_analyst",
        memory=state.get("task_memory", {}),
    )

    return {
        **state,
        "valuation_analysis": {
            "raw": valuation,
            "date_range": date_range,
            "analysis": analysis,
        },
        "tool_calls": tool_calls,
        "observations": observations,
        "analyst_notes": {
            **state.get("analyst_notes", {}),
            "valuation": analysis,
        },
        "reasoning_summary": {
            **state.get("reasoning_summary", {}),
            "valuation": analysis.get("reasoning_summary", []),
        },
        "warnings": warnings,
    }
