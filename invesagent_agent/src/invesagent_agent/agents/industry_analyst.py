from __future__ import annotations

from invesagent_agent.agents.base import default_analysis, get_module_date_range
from invesagent_agent.prompts.industry_analyst import INDUSTRY_ANALYST_PROMPT
from invesagent_agent.runtime.agent_runtime import AgentRuntime
from invesagent_agent.workflows.research_state import ResearchState


def run_industry_analyst(state: ResearchState) -> ResearchState:
    """Analyze industry universe through MCP, then let the LLM interpret it."""
    runtime = AgentRuntime(state, "industry_analyst")
    industry = state.get("industry")
    if not industry:
        return runtime.finish({"industry_analysis": {"skipped": True, "message": "未识别到行业。"}})

    market = state.get("market", "cn")
    provider = state.get("provider", "auto")
    start_date, end_date = get_module_date_range(state, "industry")
    date_range = {"start_date": start_date, "end_date": end_date}

    members = runtime.call_tool(
        "get_industry_members_tool",
        {
            "industry": industry,
            "market": market,
            "provider": provider,
            "limit": state.get("industry_member_limit", 10),
        },
        observation={"industry": industry},
    )
    observations = list(state.get("observations", []))
    if observations:
        observations[-1]["count"] = members.get("count")
        state["observations"] = observations

    member_symbols = [
        member.get("symbol")
        for member in members.get("members", [])[:8]
        if member.get("symbol")
    ] if members.get("success") else []

    comparison = None
    if len(member_symbols) >= 2 and start_date and end_date:
        comparison = runtime.call_tool(
            "compare_ohlcv_instruments_tool",
            {
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
        )
    elif len(member_symbols) >= 2:
        warnings = list(state.get("warnings", []))
        warnings.append("行业同行比较已跳过：缺少 start_date 或 end_date")
        state["warnings"] = warnings

    if not members.get("success"):
        warnings = list(state.get("warnings", []))
        warnings.append(f"行业成分股不可用：{members.get('error_type') or members.get('message')}")
        state["warnings"] = warnings

    raw = {
        "industry": industry,
        "members": members,
        "peer_comparison": comparison,
        "policy_and_dynamics": {
            "status": "not_connected",
            "message": "政策、新闻和行业动态检索尚未接入。",
        },
    }
    analysis = runtime.call_llm_json(
        system_prompt=INDUSTRY_ANALYST_PROMPT,
        context=runtime.context({"date_range": date_range, "raw": raw}),
        fallback=default_analysis(
            summary="行业 MCP 工具已完成调用，但 LLM 解读不可用。",
            key_findings=[
                f"识别到行业：{industry}。",
                f"行业样本数量：{members.get('count') or len(members.get('members', []))}。",
            ],
            data_limits=["政策、新闻和行业动态检索尚未接入。"],
        ),
    )
    final_response = analysis.get("summary") or "行业分析已完成。"
    findings = analysis.get("key_findings", [])
    if findings:
        final_response = "\n".join([final_response, *[f"- {item}" for item in findings[:5]]])

    return runtime.finish(
        {
            "industry_analysis": {
                "raw": raw,
                "date_range": date_range,
                "analysis": analysis,
            },
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
        }
    )
