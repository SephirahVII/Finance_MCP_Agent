from __future__ import annotations

from invesagent_core.services.data.sector_data import get_sector_quotes


def register_sector_data_tools(mcp) -> None:
    """Register sector data MCP tools."""

    @mcp.tool()
    def get_sector_quotes_tool(
        market: str = "cn",
        provider: str = "auto",
        keyword: str = "",
        limit: int = 100,
    ) -> dict:
        """Fetch industry/concept sector quotes."""
        result = get_sector_quotes(
            market=market,
            provider=provider,
            keyword=keyword or None,
            limit=limit,
        )
        data = result.to_dict()
        data["count"] = len(result.records)
        data["records"] = data["records"][:limit]
        return data
