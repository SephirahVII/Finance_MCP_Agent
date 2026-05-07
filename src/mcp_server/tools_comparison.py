from __future__ import annotations

from src.services.analysis.multivariate import compare_ohlcv_with_benchmark


def register_comparison_tools(mcp) -> None:
    """Register comparison MCP tools."""

    @mcp.tool()
    def compare_ohlcv_with_benchmark_tool(
        primary_symbol: str,
        benchmark_symbol: str,
        market: str,
        start_date: str,
        end_date: str,
        primary_asset_type: str = "stock",
        benchmark_asset_type: str = "index",
        provider: str = "auto",
        frequency: str = "daily",
        adjust: str | None = None,
    ) -> dict:
        """Compare return, volatility, drawdown, and correlation against a benchmark."""
        result = compare_ohlcv_with_benchmark(
            primary_symbol=primary_symbol,
            benchmark_symbol=benchmark_symbol,
            market=market,
            primary_asset_type=primary_asset_type,
            benchmark_asset_type=benchmark_asset_type,
            start_date=start_date,
            end_date=end_date,
            provider=provider,
            frequency=frequency,
            adjust=adjust,
        )
        return result.to_dict()
