from __future__ import annotations

from invesagent_agent.agents.base import default_analysis, run_llm_json_node
from invesagent_agent.clients.mcp_client import call_mcp_tool
from invesagent_agent.prompts.price_volume_analyst import PRICE_VOLUME_ANALYST_PROMPT
from invesagent_agent.workflows.research_state import ResearchState


def run_price_volume_analyst(state: ResearchState) -> ResearchState:
    """Run price-volume analysis, then ask the LLM to interpret tool results."""
    warnings = list(state.get("warnings", []))
    tool_calls = list(state.get("tool_calls", []))
    observations = list(state.get("observations", []))
    symbols = state.get("symbols", [])
    market = state.get("market", "cn")
    asset_type = state.get("asset_type", "stock")
    provider = state.get("provider", "auto")
    start_date = state.get("start_date", "")
    end_date = state.get("end_date", "")

    analyses = {}
    charts = list(state.get("charts", []))

    for symbol in symbols[:5]:
        call = {
            "node": "price_volume_analyst",
            "tool": "analyze_ohlcv_price_trend_tool",
            "arguments": {
                "symbol": symbol,
                "market": market,
                "asset_type": asset_type,
                "start_date": start_date,
                "end_date": end_date,
                "provider": provider,
            },
        }
        tool_calls.append(call)
        result = call_mcp_tool(call["tool"], call["arguments"])
        analyses[symbol] = result
        warnings.extend([f"{symbol}: {warning}" for warning in result.get("warnings", [])])
        observations.append(
            {
                "node": "price_volume_analyst",
                "tool": call["tool"],
                "symbol": symbol,
                "success": result.get("success"),
            }
        )

        if result.get("success"):
            chart_call = {
                "node": "price_volume_analyst",
                "tool": "generate_ohlcv_price_chart_tool",
                "arguments": {
                    "symbol": symbol,
                    "market": market,
                    "asset_type": asset_type,
                    "start_date": start_date,
                    "end_date": end_date,
                    "provider": provider,
                    "chart_type": "candlestick",
                    "ma_windows": "5,20",
                    "show_volume": True,
                    "indicators": "bollinger,rsi,macd",
                },
            }
            tool_calls.append(chart_call)
            chart = call_mcp_tool(chart_call["tool"], chart_call["arguments"])
            charts.append(chart)
            observations.append(
                {
                    "node": "price_volume_analyst",
                    "tool": chart_call["tool"],
                    "symbol": symbol,
                    "success": chart.get("success"),
                    "path": chart.get("relative_path") or chart.get("path"),
                }
            )

    peer_comparison = None
    if len(symbols) >= 2:
        peer_call = {
            "node": "price_volume_analyst",
            "tool": "compare_ohlcv_instruments_tool",
            "arguments": {
                "symbols": ",".join(symbols[:8]),
                "market": market,
                "asset_type": asset_type,
                "start_date": start_date,
                "end_date": end_date,
                "provider": provider,
                "include_correlation": True,
                "include_valuation": True,
                "include_fundamentals": False,
            },
        }
        tool_calls.append(peer_call)
        peer_comparison = call_mcp_tool(peer_call["tool"], peer_call["arguments"])
        observations.append(
            {
                "node": "price_volume_analyst",
                "tool": peer_call["tool"],
                "success": peer_comparison.get("success"),
            }
        )

    raw = {
        "single_instrument": analyses,
        "peer_comparison": peer_comparison,
        "charts": charts,
    }
    analysis = run_llm_json_node(
        system_prompt=PRICE_VOLUME_ANALYST_PROMPT,
        context={
            "user_query": state.get("user_query"),
            "task_plan": state.get("task_plan", {}),
            "raw": raw,
        },
        fallback=default_analysis(
            summary="Price-volume MCP tools completed; LLM interpretation was unavailable.",
            key_findings=[
                f"Processed price-volume analysis for {len(analyses)} instruments.",
                f"Generated {len(charts)} chart artifacts.",
            ],
            data_limits=warnings[-5:],
        ),
        warnings=warnings,
    )

    return {
        **state,
        "price_volume_analysis": {
            "raw": raw,
            "analysis": analysis,
        },
        "charts": charts,
        "tool_calls": tool_calls,
        "observations": observations,
        "analyst_notes": {
            **state.get("analyst_notes", {}),
            "price_volume": analysis,
        },
        "reasoning_summary": {
            **state.get("reasoning_summary", {}),
            "price_volume": analysis.get("reasoning_summary", []),
        },
        "warnings": warnings,
    }
