from __future__ import annotations

from invesagent_agent.clients.mcp_client import call_mcp_tool
from invesagent_agent.workflows.research_state import ResearchState


def run_data_collector(state: ResearchState) -> ResearchState:
    """Collect basic instrument and industry universe data for downstream agents."""
    warnings = list(state.get("warnings", []))
    tool_calls = list(state.get("tool_calls", []))
    observations = list(state.get("observations", []))
    symbols = list(state.get("symbols", []))
    industry = state.get("industry")
    market = state.get("market", "cn")
    provider = state.get("provider", "auto")

    instruments = []
    for symbol in symbols:
        try:
            call = {
                "node": "data_collector",
                "tool": "resolve_instrument_tool",
                "arguments": {"query": symbol, "market": market, "provider": provider},
            }
            tool_calls.append(call)
            instruments.append(
                call_mcp_tool(
                    call["tool"],
                    call["arguments"],
                )
            )
            observations.append({"node": "data_collector", "tool": call["tool"], "symbol": symbol})
        except Exception as exc:
            warnings.append(f"resolve_instrument failed for {symbol}: {exc}")

    industry_members = None
    if industry:
        try:
            call = {
                "node": "data_collector",
                "tool": "get_industry_members_tool",
                "arguments": {
                    "industry": industry,
                    "market": market,
                    "provider": provider,
                    "limit": state.get("industry_member_limit", 10),
                },
            }
            tool_calls.append(call)
            industry_members = call_mcp_tool(
                call["tool"],
                call["arguments"],
            )
            observations.append(
                {
                    "node": "data_collector",
                    "tool": call["tool"],
                    "industry": industry,
                    "success": industry_members.get("success"),
                    "count": industry_members.get("count"),
                }
            )

            if not symbols and industry_members.get("success"):
                symbols = [
                    member.get("symbol")
                    for member in industry_members.get("members", [])[:5]
                    if member.get("symbol")
                ]
        except Exception as exc:
            warnings.append(f"get_industry_members failed for {industry}: {exc}")

    data_package = {
        "instruments": instruments,
        "industry_members": industry_members,
    }

    return {
        **state,
        "symbols": symbols,
        "data_package": data_package,
        "tool_calls": tool_calls,
        "observations": observations,
        "warnings": warnings,
    }
