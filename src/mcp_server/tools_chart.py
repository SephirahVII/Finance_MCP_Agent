from __future__ import annotations

from src.services.chart_generator import generate_price_chart, generate_stock_charts

def register_chart_tools(mcp) -> None:
    """Register chart-generation MCP tools."""

    @mcp.tool()
    def generate_price_chart_tool(
        name_or_code: str,
        start_date: str,
        end_date: str,
    ) -> dict:
        """Generate a stock close price chart with MA5 and MA20."""
        return generate_price_chart(
            name_or_code=name_or_code,
            start_date=start_date,
            end_date=end_date,
        )

    @mcp.tool()
    def generate_stock_charts_tool(
        name_or_code: str,
        start_date: str,
        end_date: str,
    ) -> dict:
        """Generate all currently supported stock charts."""
        return generate_stock_charts(
            name_or_code=name_or_code,
            start_date=start_date,
            end_date=end_date,
        )
