from __future__ import annotations

from invesagent_agent.agents.base import default_analysis, get_module_date_range
from invesagent_agent.prompts.valuation_analyst import VALUATION_ANALYST_PROMPT
from invesagent_agent.runtime.agent_runtime import AgentRuntime
from invesagent_agent.workflows.research_state import ResearchState


def run_valuation_analyst(state: ResearchState) -> ResearchState:
    """Analyze valuation, market-value, and turnover metrics through MCP."""
    runtime = AgentRuntime(state, "valuation_analyst")
    valuation = {}
    start_date, end_date = get_module_date_range(state, "valuation")
    date_range = {"start_date": start_date, "end_date": end_date}

    if not start_date or not end_date:
        message = "估值分析需要明确的开始日期和结束日期。"
        warnings = list(state.get("warnings", []))
        warnings.append("valuation_analyst skipped: missing start_date or end_date")
        state["warnings"] = warnings
        return runtime.finish(
            {
                "valuation_analysis": {
                    "raw": {},
                    "date_range": date_range,
                    "analysis": default_analysis(
                        summary=message,
                        data_limits=["缺少 start_date 或 end_date，未调用估值 MCP 工具。"],
                    ),
                },
            }
        )

    for symbol in state.get("symbols", [])[:5]:
        result = runtime.call_tool(
            "analyze_valuation_tool",
            {
                "symbol": symbol,
                "market": state.get("market", "cn"),
                "asset_type": state.get("asset_type", "stock"),
                "start_date": start_date,
                "end_date": end_date,
                "provider": state.get("provider", "auto"),
            },
            observation={"symbol": symbol},
        )
        valuation[symbol] = result
        warnings = list(state.get("warnings", []))
        if result.get("message"):
            warnings.append(
                f"{symbol}: valuation {result.get('error_type') or 'warning'} - {result.get('message')}"
            )
        warnings.extend([f"{symbol}: {warning}" for warning in result.get("warnings", [])])
        state["warnings"] = warnings
        observations = list(state.get("observations", []))
        if observations:
            observations[-1]["error_type"] = result.get("error_type")
            state["observations"] = observations

    analysis = runtime.call_llm_json(
        system_prompt=VALUATION_ANALYST_PROMPT,
        context=runtime.context({"date_range": date_range, "raw": valuation}),
        fallback=default_analysis(
            summary="估值 MCP 工具已完成调用，但 LLM 解读不可用。",
            key_findings=[f"已处理 {len(valuation)} 个标的的估值分析。"],
            data_limits=state.get("warnings", [])[-5:],
        ),
    )

    return runtime.finish(
        {
            "valuation_analysis": {
                "raw": valuation,
                "date_range": date_range,
                "analysis": analysis,
            },
            "analyst_notes": {
                **state.get("analyst_notes", {}),
                "valuation": analysis,
            },
            "reasoning_summary": {
                **state.get("reasoning_summary", {}),
                "valuation": analysis.get("reasoning_summary", []),
            },
        }
    )
