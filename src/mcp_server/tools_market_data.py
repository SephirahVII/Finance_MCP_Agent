from __future__ import annotations

from src.services.analysis.price import analyze_ohlcv_price_trend
from src.services.charts.price import generate_ohlcv_price_chart
from src.services.data.market_data import get_cn_trade_calendar, get_ohlcv


def register_market_data_tools(mcp) -> None:
    """Register unified market-data MCP tools."""

    @mcp.tool()
    def get_ohlcv_tool(
        symbol: str,
        market: str,
        start_date: str,
        end_date: str,
        asset_type: str = "stock",
        provider: str = "auto",
        frequency: str = "daily",
        adjust: str | None = None,
        limit: int = 20,
    ) -> dict:
        """Fetch unified OHLCV market data across supported providers."""
        result = get_ohlcv(
            symbol=symbol,
            market=market,
            asset_type=asset_type,
            start_date=start_date,
            end_date=end_date,
            provider=provider,
            frequency=frequency,
            adjust=adjust,
        )

        data = result.to_dict()

        if result.records:
            data["records"] = data["records"][:limit]

        data["count"] = len(result.records)
        return data

    @mcp.tool()
    def analyze_ohlcv_price_trend_tool(
        symbol: str,
        market: str,
        start_date: str,
        end_date: str,
        asset_type: str = "stock",
        provider: str = "auto",
        frequency: str = "daily",
        adjust: str | None = None,
    ) -> dict:
        """Analyze price trend using unified OHLCV data across supported providers."""
        result = analyze_ohlcv_price_trend(
            symbol=symbol,
            market=market,
            asset_type=asset_type,
            start_date=start_date,
            end_date=end_date,
            provider=provider,
            frequency=frequency,
            adjust=adjust,
        )
        return result.to_dict()

    @mcp.tool()
    def generate_ohlcv_price_chart_tool(
        symbol: str,
        market: str,
        start_date: str,
        end_date: str,
        asset_type: str = "stock",
        provider: str = "auto",
        chart_type: str = "line",
        ma_windows: str = "5,20,60",
        show_volume: bool = False,
        frequency: str = "daily",
        adjust: str | None = None,
    ) -> dict:
        """Generate a price chart using unified OHLCV data across supported providers."""
        return generate_ohlcv_price_chart(
            symbol=symbol,
            market=market,
            asset_type=asset_type,
            start_date=start_date,
            end_date=end_date,
            provider=provider,
            chart_type=chart_type,
            ma_windows=ma_windows,
            show_volume=show_volume,
            frequency=frequency,
            adjust=adjust,
        )

    @mcp.tool()
    def get_trade_calendar_tool(
        start_date: str,
        end_date: str,
        exchange: str = "SSE",
        is_open: str | None = None,
        provider: str = "auto",
        limit: int = 50,
    ) -> dict:
        """Fetch China market trade calendar records."""
        result = get_cn_trade_calendar(
            start_date=start_date,
            end_date=end_date,
            exchange=exchange,
            is_open=is_open,
            provider=provider,
        )

        if result.get("records"):
            result["records"] = result["records"][:limit]

        return result
