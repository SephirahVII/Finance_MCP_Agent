from __future__ import annotations

from invesagent_core.services.data.index_data import get_index_weights


def register_index_data_tools(mcp) -> None:
    """Register index data MCP tools."""

    @mcp.tool()
    def get_index_weights_tool(
        index_code: str,
        market: str = "cn",
        start_date: str = "",
        end_date: str = "",
        provider: str = "auto",
        limit: int = 100,
    ) -> dict:
        """Fetch index constituents and weights."""
        result = get_index_weights(
            index_code=index_code,
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
