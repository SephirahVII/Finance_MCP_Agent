from __future__ import annotations

from typing import Any


class EvalMockToolClient:
    """Deterministic MCP tool client used by evals."""

    def __init__(self) -> None:
        self.calls: list[dict[str, Any]] = []

    def call_tool(self, name: str, arguments: dict[str, Any] | None = None) -> dict[str, Any]:
        arguments = arguments or {}
        self.calls.append({"tool": name, "arguments": arguments})

        if name == "list_industries_tool":
            return {"success": True, "industries": ["liquor", "banking", "new energy"]}
        if name == "resolve_instrument_tool":
            query = str(arguments.get("query") or "600519.SH")
            symbol = "600519.SH" if "600519" in query or "maotai" in query.lower() else query
            return {"success": True, "symbol": symbol, "name": "Kweichow Moutai", "market": "cn"}
        if name == "get_industry_members_tool":
            return {
                "success": True,
                "count": 2,
                "members": [
                    {"symbol": "600519.SH", "name": "Kweichow Moutai"},
                    {"symbol": "000858.SZ", "name": "Wuliangye"},
                ],
            }
        if name == "analyze_ohlcv_price_trend_tool":
            return {
                "success": True,
                "summary": "mock price trend analysis",
                "metrics": {"return_pct": 8.5, "volatility": 0.21, "max_drawdown": -0.07},
                "warnings": [],
            }
        if name == "generate_ohlcv_price_chart_tool":
            return {"success": True, "relative_path": "charts/eval_price.html", "warnings": []}
        if name == "get_valuation_tool":
            return {"success": True, "items": [{"symbol": "600519.SH", "pe": 25.0, "pb": 8.0}]}
        if name == "analyze_valuation_tool":
            return {"success": True, "summary": "mock valuation analysis", "warnings": []}
        if name == "get_fundamentals_tool":
            return {
                "success": True,
                "items": [{"symbol": "600519.SH", "roe": 0.28, "revenue_growth": 0.12}],
            }
        if name == "analyze_fundamentals_tool":
            return {"success": True, "summary": "mock fundamentals analysis", "warnings": []}
        if name in {
            "get_macro_data_tool",
            "get_index_weights_tool",
            "get_sector_quotes_tool",
            "get_news_or_research_tool",
            "get_company_announcements_tool",
            "get_money_flow_tool",
            "get_dividends_tool",
            "get_top_shareholders_tool",
            "get_ohlcv_tool",
            "get_trade_calendar_tool",
            "compare_ohlcv_with_benchmark_tool",
            "compare_ohlcv_instruments_tool",
        }:
            return {"success": True, "tool": name, "items": [], "warnings": []}
        return {"success": True, "tool": name, "warnings": []}

