from __future__ import annotations

from invesagent_agent.agents.base import default_analysis, run_llm_json_node
from invesagent_agent.clients.mcp_client import call_mcp_tool
from invesagent_agent.prompts.fundamental_analyst import FUNDAMENTAL_ANALYST_PROMPT
from invesagent_agent.workflows.research_state import ResearchState


def run_fundamental_analyst(state: ResearchState) -> ResearchState:
    """Analyze fundamentals through MCP, then let the LLM interpret the results."""
    warnings = list(state.get("warnings", []))
    tool_calls = list(state.get("tool_calls", []))
    observations = list(state.get("observations", []))
    fundamentals = {}

    for symbol in state.get("symbols", [])[:5]:
        call = {
            "node": "fundamental_analyst",
            "tool": "analyze_fundamentals_tool",
            "arguments": {
                "symbol": symbol,
                "market": state.get("market", "cn"),
                "asset_type": state.get("asset_type", "stock"),
                "start_date": state.get("start_date", ""),
                "end_date": state.get("end_date", ""),
                "provider": state.get("provider", "auto"),
            },
        }
        tool_calls.append(call)
        result = call_mcp_tool(call["tool"], call["arguments"])
        fundamentals[symbol] = result
        warnings.extend([f"{symbol}: {warning}" for warning in result.get("warnings", [])])
        observations.append(
            {
                "node": "fundamental_analyst",
                "tool": call["tool"],
                "symbol": symbol,
                "success": result.get("success"),
            }
        )

    analysis = run_llm_json_node(
        system_prompt=FUNDAMENTAL_ANALYST_PROMPT,
        context={
            "user_query": state.get("user_query"),
            "task_plan": state.get("task_plan", {}),
            "raw": fundamentals,
        },
        fallback=default_analysis(
            summary="Fundamental MCP tools completed; LLM interpretation was unavailable.",
            key_findings=[f"Processed fundamental analysis for {len(fundamentals)} instruments."],
            data_limits=warnings[-5:],
        ),
        warnings=warnings,
    )

    return {
        **state,
        "fundamental_analysis": {
            "raw": fundamentals,
            "analysis": analysis,
        },
        "tool_calls": tool_calls,
        "observations": observations,
        "analyst_notes": {
            **state.get("analyst_notes", {}),
            "fundamentals": analysis,
        },
        "reasoning_summary": {
            **state.get("reasoning_summary", {}),
            "fundamentals": analysis.get("reasoning_summary", []),
        },
        "warnings": warnings,
    }
