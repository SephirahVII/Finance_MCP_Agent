from __future__ import annotations

from invesagent_core.services.data.macro_data import get_macro_data


def register_macro_data_tools(mcp) -> None:
    """Register macro data MCP tools."""

    @mcp.tool()
    def get_macro_data_tool(
        indicator: str = "cpi",
        market: str = "cn",
        start_date: str = "",
        end_date: str = "",
        provider: str = "auto",
        limit: int = 100,
    ) -> dict:
        """Fetch macro data such as CPI, PMI, money supply, social financing, FX, or commodity data."""
        result = get_macro_data(
            indicator=indicator,
            market=market,
            start_date=start_date,
            end_date=end_date,
            provider=provider,
            limit=limit,
        )
        data = result.to_dict()
        data["count"] = len(result.records)
        data["records"] = data["records"][:limit]
        return data
