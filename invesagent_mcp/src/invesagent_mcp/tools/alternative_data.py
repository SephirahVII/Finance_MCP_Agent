from __future__ import annotations

from invesagent_core.services.data.alternative_data import get_alternative_data


def _fetch(
    category: str,
    market: str,
    symbol: str | None,
    start_date: str | None,
    end_date: str | None,
    provider: str,
    keyword: str | None,
    limit: int,
) -> dict:
    result = get_alternative_data(
        category=category,
        market=market,
        symbol=symbol,
        start_date=start_date,
        end_date=end_date,
        provider=provider,
        keyword=keyword,
        limit=limit,
    )
    data = result.to_dict()
    data["count"] = len(result.records)
    if result.records:
        data["records"] = data["records"][:limit]
    return data


def register_alternative_data_tools(mcp) -> None:
    """Register extended financial dataset tools."""

    @mcp.tool()
    def get_company_announcements_tool(
        symbol: str = "",
        market: str = "cn",
        start_date: str = "",
        end_date: str = "",
        provider: str = "auto",
        keyword: str = "",
        limit: int = 50,
    ) -> dict:
        """Fetch company announcements."""
        return _fetch("announcements", market, symbol or None, start_date, end_date, provider, keyword or None, limit)

    @mcp.tool()
    def get_financial_disclosure_dates_tool(
        symbol: str = "",
        market: str = "cn",
        start_date: str = "",
        end_date: str = "",
        provider: str = "auto",
        limit: int = 50,
    ) -> dict:
        """Fetch financial report disclosure dates."""
        return _fetch("financial_disclosure_dates", market, symbol or None, start_date, end_date, provider, None, limit)

    @mcp.tool()
    def get_dividends_tool(
        symbol: str,
        market: str = "cn",
        start_date: str = "",
        end_date: str = "",
        provider: str = "auto",
        limit: int = 50,
    ) -> dict:
        """Fetch dividend and bonus-share events."""
        return _fetch("dividends", market, symbol, start_date, end_date, provider, None, limit)

    @mcp.tool()
    def get_shareholder_counts_tool(
        symbol: str,
        market: str = "cn",
        start_date: str = "",
        end_date: str = "",
        provider: str = "auto",
        limit: int = 50,
    ) -> dict:
        """Fetch shareholder count history."""
        return _fetch("shareholder_counts", market, symbol, start_date, end_date, provider, None, limit)

    @mcp.tool()
    def get_top_shareholders_tool(
        symbol: str,
        market: str = "cn",
        start_date: str = "",
        end_date: str = "",
        provider: str = "auto",
        float_only: bool = False,
        limit: int = 50,
    ) -> dict:
        """Fetch top shareholders or top float shareholders."""
        category = "float_top_shareholders" if float_only else "top_shareholders"
        return _fetch(category, market, symbol, start_date, end_date, provider, None, limit)

    @mcp.tool()
    def get_institution_holding_and_northbound_tool(
        symbol: str = "",
        market: str = "cn",
        start_date: str = "",
        end_date: str = "",
        provider: str = "auto",
        keyword: str = "northbound",
        limit: int = 50,
    ) -> dict:
        """Fetch institution holding related data or northbound capital data where supported."""
        category = "northbound_capital" if keyword in {"northbound", "hsgt", "北向"} else "top_shareholders"
        return _fetch(category, market, symbol or None, start_date, end_date, provider, keyword, limit)

    @mcp.tool()
    def get_dragon_tiger_tool(
        symbol: str = "",
        market: str = "cn",
        start_date: str = "",
        end_date: str = "",
        provider: str = "auto",
        limit: int = 50,
    ) -> dict:
        """Fetch China A-share Dragon Tiger list data."""
        return _fetch("dragon_tiger", market, symbol or None, start_date, end_date, provider, None, limit)

    @mcp.tool()
    def get_block_trades_tool(
        symbol: str = "",
        market: str = "cn",
        start_date: str = "",
        end_date: str = "",
        provider: str = "auto",
        limit: int = 50,
    ) -> dict:
        """Fetch block trade data."""
        return _fetch("block_trades", market, symbol or None, start_date, end_date, provider, None, limit)

    @mcp.tool()
    def get_money_flow_tool(
        symbol: str = "",
        market: str = "cn",
        start_date: str = "",
        end_date: str = "",
        provider: str = "auto",
        limit: int = 50,
    ) -> dict:
        """Fetch money-flow data."""
        return _fetch("money_flow", market, symbol or None, start_date, end_date, provider, None, limit)
