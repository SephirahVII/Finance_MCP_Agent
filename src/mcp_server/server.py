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


def create_mcp_server():
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


    mcp = FastMCP(SERVER_NAME)
    mcp.tool()(health_check)
    mcp.tool()(get_project_info)
    register_stock_tools(mcp)
    register_analysis_tools(mcp)
    register_chart_tools(mcp)


    return mcp

def main() -> None:
    mcp = create_mcp_server()
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
