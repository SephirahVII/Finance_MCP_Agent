from __future__ import annotations

from invesagent_core.services.data.news_research import get_news_or_research


def register_news_research_tools(mcp) -> None:
    """Register news and research report MCP tools."""

    @mcp.tool()
    def get_news_or_research_tool(
        symbol: str = "",
        market: str = "cn",
        provider: str = "auto",
        keyword: str = "news",
        start_date: str = "",
        end_date: str = "",
        limit: int = 50,
    ) -> dict:
        """Fetch news or research report metadata where supported."""
        result = get_news_or_research(
            symbol=symbol or None,
            market=market,
            provider=provider,
            keyword=keyword,
            start_date=start_date or None,
            end_date=end_date or None,
            limit=limit,
        )
        data = result.to_dict()
        data["count"] = len(result.records)
        data["records"] = data["records"][:limit]
        return data
