from __future__ import annotations

from invesagent_agent.agents.base import default_analysis, get_module_date_range
from invesagent_agent.prompts.fundamental_analyst import FUNDAMENTAL_ANALYST_PROMPT
from invesagent_agent.runtime.agent_runtime import AgentRuntime
from invesagent_agent.workflows.research_state import ResearchState


def run_fundamental_analyst(state: ResearchState) -> ResearchState:
    """Analyze fundamentals through MCP, then let the LLM interpret the results."""
    runtime = AgentRuntime(state, "fundamental_analyst")
    fundamentals = {}
    start_date, end_date = get_module_date_range(state, "fundamentals")
    date_range = {"start_date": start_date, "end_date": end_date}

    if not start_date or not end_date:
        message = "基本面分析需要明确的开始日期和结束日期，请补充时间范围，例如：2024-01-01 到 2024-12-31。"
        warnings = list(state.get("warnings", []))
        warnings.append("fundamental_analyst skipped: missing start_date or end_date")
        state["warnings"] = warnings
        return runtime.finish(
            {
                "fundamental_analysis": {
                    "raw": {},
                    "date_range": date_range,
                    "analysis": default_analysis(
                        summary=message,
                        data_limits=["缺少 start_date 或 end_date，未调用基本面 MCP 工具。"],
                    ),
                },
                "final_response": message,
                "final_report": message,
            }
        )

    for symbol in state.get("symbols", [])[:5]:
        result = runtime.call_tool(
            "analyze_fundamentals_tool",
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
        fundamentals[symbol] = result
        warnings = list(state.get("warnings", []))
        warnings.extend([f"{symbol}: {warning}" for warning in result.get("warnings", [])])
        state["warnings"] = warnings

    analysis = runtime.call_llm_json(
        system_prompt=FUNDAMENTAL_ANALYST_PROMPT,
        context=runtime.context({"date_range": date_range, "raw": fundamentals}),
        fallback=default_analysis(
            summary="基本面 MCP 工具已完成调用，但 LLM 解读不可用。",
            key_findings=[f"已处理 {len(fundamentals)} 个标的的基本面分析。"],
            data_limits=state.get("warnings", [])[-5:],
        ),
    )
    final_response = analysis.get("summary") or "基本面分析已完成。"
    findings = analysis.get("key_findings", [])
    if findings:
        final_response = "\n".join([final_response, *[f"- {item}" for item in findings[:5]]])

    return runtime.finish(
        {
            "fundamental_analysis": {
                "raw": fundamentals,
                "date_range": date_range,
                "analysis": analysis,
            },
            "analyst_notes": {
                **state.get("analyst_notes", {}),
                "fundamentals": analysis,
            },
            "reasoning_summary": {
                **state.get("reasoning_summary", {}),
                "fundamentals": analysis.get("reasoning_summary", []),
            },
            "final_response": final_response,
            "final_report": final_response,
        }
    )
