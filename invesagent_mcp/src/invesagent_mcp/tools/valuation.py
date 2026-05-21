from __future__ import annotations

from invesagent_core.services.analysis.valuation import analyze_valuation
from invesagent_core.services.data.valuation import get_valuation


def register_valuation_tools(mcp) -> None:
    """Register unified valuation MCP tools."""

    @mcp.tool()
    def get_valuation_tool(
        symbol: str,
        market: str,
        start_date: str,
        end_date: str,
        asset_type: str = "stock",
        provider: str = "auto",
        limit: int = 20,
    ) -> dict:
        """Fetch unified valuation and trading-metric data across supported providers."""
        result = get_valuation(
            symbol=symbol,
            market=market,
            asset_type=asset_type,
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
    def analyze_valuation_tool(
        symbol: str,
        market: str,
        start_date: str,
        end_date: str,
        asset_type: str = "stock",
        provider: str = "auto",
    ) -> dict:
        """Analyze valuation metrics such as PE, PB, turnover, and market value."""
        result = analyze_valuation(
            symbol=symbol,
            market=market,
            asset_type=asset_type,
            start_date=start_date,
            end_date=end_date,
            provider=provider,
        )
        return result.to_dict()
