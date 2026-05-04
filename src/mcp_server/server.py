from __future__ import annotations

import argparse

from src.config.settings import settings


SERVER_NAME = "tushare-financial-analyst"


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
        "project_name": "tushare-ai-financial-agent",
        "server_name": SERVER_NAME,
        "agent_name": "A股金融分析师",
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

    from src.mcp_server.tools_stock import register_stock_tools
    from src.mcp_server.tools_analysis import register_analysis_tools
    from src.mcp_server.tools_chart import register_chart_tools


    mcp = FastMCP(
        SERVER_NAME,
        host=host or settings.mcp_host,
        port=port or settings.mcp_port,
        streamable_http_path=streamable_http_path or settings.mcp_streamable_http_path,
    )
    mcp.tool()(health_check)
    mcp.tool()(get_project_info)
    register_stock_tools(mcp)
    register_analysis_tools(mcp)
    register_chart_tools(mcp)

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
