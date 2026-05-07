from __future__ import annotations

from src.services.data.instruments import resolve_instrument


def register_instrument_tools(mcp) -> None:
    """Register unified instrument MCP tools."""

    @mcp.tool()
    def resolve_instrument_tool(
        query: str,
        market: str | None = None,
        asset_type: str | None = None,
        provider: str = "auto",
    ) -> dict:
        """Resolve user input to a unified financial instrument."""
        instrument = resolve_instrument(
            query=query,
            market=market,
            asset_type=asset_type,
            provider=provider,
        )
        return instrument.to_dict()
