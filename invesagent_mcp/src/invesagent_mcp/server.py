from __future__ import annotations

import argparse

from invesagent_core.config.settings import settings


SERVER_NAME = "invesagent-finance-mcp"


def health_check() -> dict:
    """Return a simple health check for the MCP server."""
    return {
        "server_name": SERVER_NAME,
        "status": "ok",
        "data_provider": "Tushare Pro",
    }


def get_project_info() -> dict:
    """Return project metadata and current default configuration."""
    return {
        "project_name": "InvesAgent MCP",
        "server_name": SERVER_NAME,
        "agent_name": "InvesAgent Research Agent",
        "default_index_code": settings.default_index_code,
        "report_writing_mode": settings.report_writing_mode,
        "data_cache_dir": settings.data_cache_dir,
        "charts_dir": settings.charts_dir,
        "reports_dir": settings.reports_dir,
        "tushare_token_configured": bool(settings.tushare_token),
    }


def create_mcp_server(
    host: str | None = None,
    port: int | None = None,
    streamable_http_path: str | None = None,
):
    """Create the FastMCP server and register tools.

    The import is intentionally lazy so the project can be studied and smoke-tested
    before external dependencies are installed.
    """
    try:
        from mcp.server.fastmcp import FastMCP
    except ModuleNotFoundError as exc:
        raise RuntimeError(
            "The 'mcp' package is not installed. Install dependencies with `pip install mcp`."
        ) from exc

    from invesagent_mcp.tools.instruments import register_instrument_tools
    from invesagent_mcp.tools.market_data import register_market_data_tools
    from invesagent_mcp.tools.valuation import register_valuation_tools
    from invesagent_mcp.tools.fundamentals import register_fundamentals_tools
    from invesagent_mcp.tools.comparison import register_comparison_tools
    from invesagent_mcp.tools.industry import register_industry_tools
    from invesagent_mcp.tools.alternative_data import register_alternative_data_tools
    from invesagent_mcp.tools.index_data import register_index_data_tools
    from invesagent_mcp.tools.macro_data import register_macro_data_tools
    from invesagent_mcp.tools.news_research import register_news_research_tools
    from invesagent_mcp.tools.sector_data import register_sector_data_tools

    mcp = FastMCP(
        SERVER_NAME,
        host=host or settings.mcp_host,
        port=port or settings.mcp_port,
        streamable_http_path=streamable_http_path or settings.mcp_streamable_http_path,
    )
    mcp.tool()(health_check)
    mcp.tool()(get_project_info)
    register_instrument_tools(mcp)
    register_market_data_tools(mcp)
    register_valuation_tools(mcp)
    register_fundamentals_tools(mcp)
    register_comparison_tools(mcp)
    register_industry_tools(mcp)
    register_alternative_data_tools(mcp)
    register_macro_data_tools(mcp)
    register_sector_data_tools(mcp)
    register_index_data_tools(mcp)
    register_news_research_tools(mcp)

    return mcp


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the Tushare Financial Analyst MCP Server.")
    parser.add_argument(
        "--transport",
        choices=["stdio", "streamable-http"],
        default=settings.mcp_transport,
        help="MCP transport to use.",
    )
    parser.add_argument(
        "--host",
        default=settings.mcp_host,
        help="Host for streamable-http transport.",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=settings.mcp_port,
        help="Port for streamable-http transport.",
    )
    parser.add_argument(
        "--path",
        default=settings.mcp_streamable_http_path,
        help="Streamable HTTP endpoint path.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    mcp = create_mcp_server(
        host=args.host,
        port=args.port,
        streamable_http_path=args.path,
    )
    mcp.run(transport=args.transport)


if __name__ == "__main__":
    main()
