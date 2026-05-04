from __future__ import annotations

from src.services.analyzer import analyze_price_trend

def register_analysis_tools(mcp) -> None:
    """Register analysis-related MCP tools."""

    @mcp.tool()
    def analyze_price_trend_tool(
        name_or_code: str,
        start_date: str,
        end_date: str,
    ) -> dict:
        """Analyze price trend metrics for a Chinese A-share stock."""
        return analyze_price_trend(
            name_or_code=name_or_code,
            start_date=start_date,
            end_date=end_date,
        )