from __future__ import annotations

from invesagent_agent.runtime.agent_runtime import AgentRuntime
from invesagent_agent.workflows.research_state import ResearchState


def run_data_collector(state: ResearchState) -> ResearchState:
    """Collect basic instrument and industry universe data for downstream agents."""
    runtime = AgentRuntime(state, "data_collector")
    symbols = list(state.get("symbols", []))
    industry = state.get("industry")
    market = state.get("market", "cn")
    provider = state.get("provider", "auto")

    instruments = []
    for symbol in symbols:
        try:
            instruments.append(
                runtime.call_tool(
                    "resolve_instrument_tool",
                    {"query": symbol, "market": market, "provider": provider},
                    observation={"symbol": symbol},
                )
            )
        except Exception as exc:
            warnings = list(state.get("warnings", []))
            warnings.append(f"resolve_instrument failed for {symbol}: {exc}")
            state["warnings"] = warnings

    industry_members = None
    if industry:
        try:
            industry_members = runtime.call_tool(
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
                observations[-1]["count"] = industry_members.get("count")
                state["observations"] = observations

            if not symbols and industry_members.get("success"):
                symbols = [
                    member.get("symbol")
                    for member in industry_members.get("members", [])[:5]
                    if member.get("symbol")
                ]
        except Exception as exc:
            warnings = list(state.get("warnings", []))
            warnings.append(f"get_industry_members failed for {industry}: {exc}")
            state["warnings"] = warnings

    data_package = {
        "instruments": instruments,
        "industry_members": industry_members,
    }

    return runtime.finish(
        {
            "symbols": symbols,
            "data_package": data_package,
        }
    )
