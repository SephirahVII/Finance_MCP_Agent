from __future__ import annotations

from invesagent_agent.agents.base import (
    default_analysis,
    get_module_date_range,
    run_llm_json_node,
    run_mcp_tool_node,
)
from invesagent_agent.prompts.industry_analyst import INDUSTRY_ANALYST_PROMPT
from invesagent_agent.workflows.research_state import ResearchState


def run_industry_analyst(state: ResearchState) -> ResearchState:
    """Analyze industry universe through MCP, then let the LLM interpret it."""
    industry = state.get("industry")
    if not industry:
        skipped = {"skipped": True, "message": "未识别到行业。"}
        return {**state, "industry_analysis": skipped}

    warnings = list(state.get("warnings", []))
    tool_calls = list(state.get("tool_calls", []))
    observations = list(state.get("observations", []))
    market = state.get("market", "cn")
    provider = state.get("provider", "auto")
    start_date, end_date = get_module_date_range(state, "industry")
    date_range = {"start_date": start_date, "end_date": end_date}

    members = run_mcp_tool_node(
        node="industry_analyst",
        tool="get_industry_members_tool",
        arguments={
            "industry": industry,
            "market": market,
            "provider": provider,
            "limit": state.get("industry_member_limit", 10),
        },
        tool_calls=tool_calls,
        observations=observations,
        warnings=warnings,
        observation={"industry": industry},
        state=state,
    )
    if observations:
        observations[-1]["count"] = members.get("count")

    member_symbols = [
        member.get("symbol")
        for member in members.get("members", [])[:8]
        if member.get("symbol")
    ] if members.get("success") else []

    comparison = None
    if len(member_symbols) >= 2 and start_date and end_date:
        comparison = run_mcp_tool_node(
            node="industry_analyst",
            tool="compare_ohlcv_instruments_tool",
            arguments={
                "symbols": ",".join(member_symbols),
                "market": market,
                "asset_type": state.get("asset_type", "stock"),
                "start_date": start_date,
                "end_date": end_date,
                "provider": provider,
                "include_correlation": True,
                "include_valuation": True,
                "include_fundamentals": False,
            },
            tool_calls=tool_calls,
            observations=observations,
            warnings=warnings,
            state=state,
        )
    elif len(member_symbols) >= 2:
        warnings.append("行业同行比较已跳过：缺少 start_date 或 end_date")

    if not members.get("success"):
        warnings.append(
            f"行业成分股不可用：{members.get('error_type') or members.get('message')}"
        )

    raw = {
        "industry": industry,
        "members": members,
        "peer_comparison": comparison,
        "policy_and_dynamics": {
            "status": "not_connected",
            "message": "政策、新闻和行业动态检索尚未接入。",
        },
    }
    analysis = run_llm_json_node(
        system_prompt=INDUSTRY_ANALYST_PROMPT,
        context={
            "user_query": state.get("user_query"),
            "task_plan": state.get("task_plan", {}),
            "date_range": date_range,
            "user_date_range": state.get("user_date_range", {}),
            "raw": raw,
        },
        fallback=default_analysis(
            summary="行业 MCP 工具已完成调用，但 LLM 解读不可用。",
            key_findings=[
                f"识别到行业：{industry}。",
                f"行业样本数量：{members.get('count') or len(members.get('members', []))}。",
            ],
            data_limits=["政策、新闻和行业动态检索尚未接入。"],
        ),
        warnings=warnings,
        role="industry_analyst",
        memory=state.get("task_memory", {}),
    )
    final_response = analysis.get("summary") or "行业分析已完成。"
    findings = analysis.get("key_findings", [])
    if findings:
        final_response = "\n".join([final_response, *[f"- {item}" for item in findings[:5]]])

    return {
        **state,
        "industry_analysis": {
            "raw": raw,
            "date_range": date_range,
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
        "final_response": final_response,
        "final_report": final_response,
        "warnings": warnings,
    }
