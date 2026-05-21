from __future__ import annotations

from invesagent_agent.agents.base import default_analysis, run_llm_json_node
from invesagent_agent.clients.mcp_client import call_mcp_tool
from invesagent_agent.prompts.industry_analyst import INDUSTRY_ANALYST_PROMPT
from invesagent_agent.workflows.research_state import ResearchState


def run_industry_analyst(state: ResearchState) -> ResearchState:
    """Analyze industry universe through MCP, then let the LLM interpret it."""
    industry = state.get("industry")
    if not industry:
        skipped = {"skipped": True, "message": "No industry detected."}
        return {**state, "industry_analysis": skipped}

    warnings = list(state.get("warnings", []))
    tool_calls = list(state.get("tool_calls", []))
    observations = list(state.get("observations", []))
    market = state.get("market", "cn")
    provider = state.get("provider", "auto")

    member_call = {
        "node": "industry_analyst",
        "tool": "get_industry_members_tool",
        "arguments": {
            "industry": industry,
            "market": market,
            "provider": provider,
            "limit": state.get("industry_member_limit", 10),
        },
    }
    tool_calls.append(member_call)
    members = call_mcp_tool(member_call["tool"], member_call["arguments"])
    observations.append(
        {
            "node": "industry_analyst",
            "tool": member_call["tool"],
            "industry": industry,
            "success": members.get("success"),
            "count": members.get("count"),
        }
    )

    member_symbols = [
        member.get("symbol")
        for member in members.get("members", [])[:8]
        if member.get("symbol")
    ] if members.get("success") else []

    comparison = None
    if len(member_symbols) >= 2:
        comparison_call = {
            "node": "industry_analyst",
            "tool": "compare_ohlcv_instruments_tool",
            "arguments": {
                "symbols": ",".join(member_symbols),
                "market": market,
                "asset_type": state.get("asset_type", "stock"),
                "start_date": state.get("start_date", ""),
                "end_date": state.get("end_date", ""),
                "provider": provider,
                "include_correlation": True,
                "include_valuation": True,
                "include_fundamentals": False,
            },
        }
        tool_calls.append(comparison_call)
        comparison = call_mcp_tool(comparison_call["tool"], comparison_call["arguments"])
        observations.append(
            {
                "node": "industry_analyst",
                "tool": comparison_call["tool"],
                "success": comparison.get("success"),
            }
        )

    if not members.get("success"):
        warnings.append(
            f"industry members unavailable: {members.get('error_type') or members.get('message')}"
        )

    raw = {
        "industry": industry,
        "members": members,
        "peer_comparison": comparison,
        "policy_and_dynamics": {
            "status": "not_connected",
            "message": "Policy, news, and industry dynamics retrieval is not connected yet.",
        },
    }
    analysis = run_llm_json_node(
        system_prompt=INDUSTRY_ANALYST_PROMPT,
        context={
            "user_query": state.get("user_query"),
            "task_plan": state.get("task_plan", {}),
            "raw": raw,
        },
        fallback=default_analysis(
            summary="Industry MCP tools completed; LLM interpretation was unavailable.",
            key_findings=[
                f"Detected industry: {industry}.",
                f"Industry sample size: {members.get('count') or len(members.get('members', []))}.",
            ],
            data_limits=["Policy, news, and industry dynamics retrieval is not connected yet."],
        ),
        warnings=warnings,
    )

    return {
        **state,
        "industry_analysis": {
            "raw": raw,
            "analysis": analysis,
        },
        "tool_calls": tool_calls,
        "observations": observations,
        "analyst_notes": {
            **state.get("analyst_notes", {}),
            "industry": analysis,
        },
        "reasoning_summary": {
            **state.get("reasoning_summary", {}),
            "industry": analysis.get("reasoning_summary", []),
        },
        "warnings": warnings,
    }
