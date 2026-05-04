from __future__ import annotations

from src.services.market_data import (
    get_daily_basic,
    get_daily_prices,
    get_stock_market_data,
)
from src.services.stock_resolver import get_stock_basic, resolve_stock_code

def register_stock_tools(mcp) -> None:
    """注册股票相关的 MCP 工具。

    输入：
        mcp：FastMCP 服务器实例，用于挂载可被客户端调用的工具函数。

    输出：
        无。函数会通过 @mcp.tool() 将股票解析和股票基础信息查询工具注册到 MCP 服务器。
    """

    @mcp.tool()
    def resolve_stock_code_tool(name_or_code: str) -> dict:
        """将中国 A 股股票名称或代码解析为 Tushare 标准 ts_code。

        输入：
            name_or_code：股票名称、股票简称、6 位股票代码或标准 ts_code。

        输出：
            返回解析结果字典，包括是否匹配、原始输入、ts_code、股票名称、
            匹配方式和结果说明等信息。
        """
        try:
            return resolve_stock_code(name_or_code)
        except Exception as exc:
            return {
                "matched": False,
                "success": False,
                "error_type": "stock_resolver_error",
                "input": name_or_code,
                "ts_code": None,
                "name": None,
                "message": "股票代码解析失败，请检查 Tushare 连接、接口频率或本地缓存。",
                "raw_error": str(exc),
            }

    @mcp.tool()
    def get_stock_basic_tool(limit: int = 20) -> dict:
        """返回已上市 A 股的基础信息。

        输入：
            limit：最多返回的股票数量，默认返回前 20 条。

        输出：
            返回字典：
            - count：Tushare 返回的股票总数量
            - items：按 limit 截取后的股票基础信息列表
        """
        try:
            stocks = get_stock_basic()
            return {
                "success": True,
                "count": len(stocks),
                "items": stocks[:limit],
            }
        except Exception as exc:
            return {
                "success": False,
                "error_type": "stock_basic_unavailable",
                "message": "股票基础信息暂不可用，请检查 Tushare 连接、接口频率或本地缓存。",
                "raw_error": str(exc),
                "count": 0,
                "items": [],
            }
    
    @mcp.tool()
    def get_daily_prices_tool(
        name_or_code: str,
        start_date: str,
        end_date: str,
        limit: int = 20,
    ) -> dict:
        """Fetch daily price data for a Chinese A-share stock."""
        return get_daily_prices(
            name_or_code=name_or_code,
            start_date=start_date,
            end_date=end_date,
            limit=limit,
        )
    
    @mcp.tool()
    def get_daily_basic_tool(
        name_or_code: str,
        start_date: str,
        end_date: str,
        limit: int = 20,
    ) -> dict:
        """Fetch daily valuation indicators if the current Tushare token has permission."""
        return get_daily_basic(
            name_or_code=name_or_code,
            start_date=start_date,
            end_date=end_date,
            limit=limit,
        )

    @mcp.tool()
    def get_stock_market_data_tool(
        name_or_code: str,
        start_date: str,
        end_date: str,
        limit: int = 20,
    ) -> dict:
        """Fetch daily price data and daily basic indicators together."""
        return get_stock_market_data(
            name_or_code=name_or_code,
            start_date=start_date,
            end_date=end_date,
            limit=limit,
        )
