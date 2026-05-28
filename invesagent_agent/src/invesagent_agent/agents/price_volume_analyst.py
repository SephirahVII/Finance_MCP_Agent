from __future__ import annotations

from invesagent_agent.agents import base as agent_base
from invesagent_agent.agents.base import default_analysis, get_module_date_range
from invesagent_agent.prompts.price_volume_analyst import PRICE_VOLUME_ANALYST_PROMPT
from invesagent_agent.runtime.agent_runtime import AgentRuntime
from invesagent_agent.workflows.research_state import ResearchState


def run_price_volume_analyst(state: ResearchState) -> ResearchState:
    """Run price-volume analysis, then ask the LLM to interpret tool results."""
    runtime = AgentRuntime(
        state,
        "price_volume_analyst",
        generate_json_fn=agent_base.generate_json,
        generate_text_fn=agent_base.generate_text,
    )
    symbols = state.get("symbols", [])
    market = state.get("market", "cn")
    asset_type = state.get("asset_type", "stock")
    provider = state.get("provider", "auto")
    start_date, end_date = get_module_date_range(state, "price_volume")
    date_range = {"start_date": start_date, "end_date": end_date}

    if not start_date or not end_date:
        message = "量价分析需要明确的开始日期和结束日期，请补充时间范围，例如：2024-01-01 到 2024-12-31。"
        warnings = list(state.get("warnings", []))
        warnings.append("price_volume_analyst skipped: missing start_date or end_date")
        state["warnings"] = warnings
        return runtime.finish(
            {
                "price_volume_analysis": {
                    "raw": {},
                    "date_range": date_range,
                    "analysis": default_analysis(
                        summary=message,
                        data_limits=["缺少 start_date 或 end_date，未调用量价 MCP 工具。"],
                    ),
                },
                "final_response": message,
                "final_report": message,
            }
        )

    analyses = {}
    charts = list(state.get("charts", []))

    for symbol in symbols[:5]:
        result = runtime.call_tool(
            "analyze_ohlcv_price_trend_tool",
            {
                "symbol": symbol,
                "market": market,
                "asset_type": asset_type,
                "start_date": start_date,
                "end_date": end_date,
                "provider": provider,
            },
            observation={"symbol": symbol},
        )
        analyses[symbol] = result
        warnings = list(state.get("warnings", []))
        warnings.extend([f"{symbol}: {warning}" for warning in result.get("warnings", [])])
        state["warnings"] = warnings

        if result.get("success"):
            chart = runtime.call_tool(
                "generate_ohlcv_price_chart_tool",
                {
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
                observation={"symbol": symbol},
            )
            charts.append(chart)
            observations = list(state.get("observations", []))
            if observations:
                observations[-1]["path"] = chart.get("relative_path") or chart.get("path")
                state["observations"] = observations

    peer_comparison = None
    if len(symbols) >= 2:
        peer_comparison = runtime.call_tool(
            "compare_ohlcv_instruments_tool",
            {
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
        )

    raw = {
        "single_instrument": analyses,
        "peer_comparison": peer_comparison,
        "charts": charts,
    }
    analysis = runtime.call_llm_json(
        system_prompt=PRICE_VOLUME_ANALYST_PROMPT,
        context=runtime.context(
            {
                "date_range": date_range,
                "raw": raw,
            }
        ),
        fallback=default_analysis(
            summary="量价 MCP 工具已完成调用，但 LLM 解读不可用。",
            key_findings=[
                f"已处理 {len(analyses)} 个标的的量价分析。",
                f"已生成 {len(charts)} 个图表产物。",
            ],
            data_limits=state.get("warnings", [])[-5:],
        ),
    )
    final_response = analysis.get("summary") or "量价分析已完成。"
    final_response = f"分析区间：{start_date} 至 {end_date}\n\n{final_response}"
    findings = analysis.get("key_findings", [])
    if findings:
        final_response = "\n".join([final_response, *[f"- {item}" for item in findings[:5]]])

    return runtime.finish(
        {
            "price_volume_analysis": {
                "raw": raw,
                "date_range": date_range,
                "analysis": analysis,
            },
            "charts": charts,
            "analyst_notes": {
                **state.get("analyst_notes", {}),
                "price_volume": analysis,
            },
            "reasoning_summary": {
                **state.get("reasoning_summary", {}),
                "price_volume": analysis.get("reasoning_summary", []),
            },
            "final_response": final_response,
            "final_report": final_response,
        }
    )
