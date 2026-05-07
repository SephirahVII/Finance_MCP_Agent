from __future__ import annotations

from src.services.analysis.fundamentals import analyze_fundamentals
from src.services.data.fundamentals import get_fundamentals


def register_fundamentals_tools(mcp) -> None:
    """Register unified fundamentals MCP tools."""

    @mcp.tool()
    def get_fundamentals_tool(
        symbol: str,
        market: str,
        data_type: str,
        start_date: str,
        end_date: str,
        asset_type: str = "stock",
        provider: str = "auto",
        limit: int = 20,
    ) -> dict:
        """Fetch financial statements or financial indicators."""
        result = get_fundamentals(
            symbol=symbol,
            market=market,
            asset_type=asset_type,
            data_type=data_type,
            start_date=start_date,
            end_date=end_date,
            provider=provider,
        )

        data = result.to_dict()

        if result.records:
            data["records"] = data["records"][:limit]

        data["count"] = len(result.records)
        return data

    @mcp.tool()
    def analyze_fundamentals_tool(
        symbol: str,
        market: str,
        start_date: str,
        end_date: str,
        asset_type: str = "stock",
        provider: str = "auto",
    ) -> dict:
        """Analyze income, balance sheet, cashflow, and financial indicator data."""
        result = analyze_fundamentals(
            symbol=symbol,
            market=market,
            asset_type=asset_type,
            start_date=start_date,
            end_date=end_date,
            provider=provider,
        )
        return result.to_dict()
