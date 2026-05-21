from __future__ import annotations

from invesagent_core.services.data.industry import get_industry_members, list_industries


def register_industry_tools(mcp) -> None:
    """Register industry universe MCP tools."""

    @mcp.tool()
    def list_industries_tool(
        market: str = "cn",
        provider: str = "auto",
        limit: int = 200,
    ) -> dict:
        """List available industries from the configured provider."""
        result = list_industries(market=market, provider=provider)

        if result.get("industries"):
            result["industries"] = result["industries"][:limit]

        return result

    @mcp.tool()
    def get_industry_members_tool(
        industry: str,
        market: str = "cn",
        provider: str = "auto",
        match_mode: str = "fuzzy",
        limit: int = 50,
    ) -> dict:
        """Get industry member stocks for horizontal peer analysis."""
        result = get_industry_members(
            industry=industry,
            market=market,
            provider=provider,
            match_mode=match_mode,
            limit=limit,
        )
        data = result.to_dict()
        data["count"] = len(result.members)
        return data

