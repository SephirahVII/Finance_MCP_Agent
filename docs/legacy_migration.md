# 旧工具迁移说明

本项目已经从早期 Tushare-only MVP 结构迁移到统一多数据源架构。旧 MCP 工具和旧 services 文件已经不再作为公开工具入口使用。

## 已移除的旧 MCP 工具

旧工具包括：

```text
resolve_stock_code_tool
get_stock_basic_tool
get_daily_prices_tool
get_daily_basic_tool
get_stock_market_data_tool
analyze_price_trend_tool
generate_price_chart_tool
generate_stock_charts_tool
```

它们曾经直接围绕 Tushare A 股数据设计，适合 MVP 阶段快速验证，但不适合后续扩展到 AkShare、Binance、港股、美股、期货、数字货币和订单簿数据。

## 当前统一 MCP 工具

当前工具减少为 6 个：

```text
health_check
get_project_info
resolve_instrument_tool
get_ohlcv_tool
analyze_ohlcv_price_trend_tool
generate_ohlcv_price_chart_tool
```

迁移关系：

| 旧能力 | 新工具 |
|---|---|
| 股票代码解析 | `resolve_instrument_tool` |
| A 股日线行情 | `get_ohlcv_tool` |
| 价格趋势分析 | `analyze_ohlcv_price_trend_tool` |
| 价格图生成 | `generate_ohlcv_price_chart_tool` |

## 仍需在新架构中补回的能力

旧版里的 `daily_basic`、股票基础信息列表、估值分析、批量图表合集等能力，不再直接用旧工具保留，而是计划按统一数据类型重新实现：

```text
src/models/valuation.py
src/providers/tushare/valuation.py
src/services/unified_valuation.py
src/mcp_server/tools_valuation.py
```

这样做的好处是：Tushare 的 `daily_basic`、AkShare 的港股/美股估值数据，以及后续其他 provider 的估值数据，可以通过同一层 service 暴露给 MCP 工具。

## 当前架构边界

```text
models/
  定义统一数据结构，不直接访问外部 API。

providers/
  处理具体数据源 API、字段转换、权限错误和数据源特有格式。

services/
  负责统一业务入口和 provider 路由，不写死某个数据源。

mcp_server/
  只负责把 services 暴露成 MCP tools。

agent/
  负责自然语言理解、工具选择和最终中文解释。
```

## 后续迁移原则

新增能力时不要回到旧式结构：

```text
不推荐：
src/services/market_data.py 同时写 Tushare 获取、分析、图表和错误处理

推荐：
src/providers/tushare/xxx.py
src/models/xxx.py
src/services/unified_xxx.py
src/mcp_server/tools_xxx.py
```

例如订单簿数据应该走：

```text
src/models/order_book.py
src/providers/binance/order_book.py
src/services/unified_order_book.py
src/mcp_server/tools_order_book.py
```

这样项目可以持续扩展，而不会重新变成单数据源脚本集合。

