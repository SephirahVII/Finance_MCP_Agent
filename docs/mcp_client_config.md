# MCP Client Configuration

This project currently exposes a local MCP Server over `stdio`.

## Generic stdio Configuration

Use the Python interpreter from the environment where dependencies are installed.

```json
{
  "mcpServers": {
    "tushareFinancialAnalyst": {
      "command": "C:\\Users\\wayne\\.conda\\envs\\tushare-agent\\python.exe",
      "args": [
        "-m",
        "src.mcp_server.server"
      ],
      "cwd": "D:\\iCloudDrive\\Projects\\QUANT\\Tushare AI Agent",
      "env": {
        "TUSHARE_TOKEN": "your_tushare_token"
      }
    }
  }
}
```

If the client does not support `cwd`, set `PYTHONPATH`:

```json
{
  "mcpServers": {
    "tushareFinancialAnalyst": {
      "command": "C:\\Users\\wayne\\.conda\\envs\\tushare-agent\\python.exe",
      "args": [
        "-m",
        "src.mcp_server.server"
      ],
      "env": {
        "PYTHONPATH": "D:\\iCloudDrive\\Projects\\QUANT\\Tushare AI Agent",
        "TUSHARE_TOKEN": "your_tushare_token"
      }
    }
  }
}
```

Do not commit real tokens to GitHub.

## Available Tools

- `health_check`
- `get_project_info`
- `resolve_stock_code_tool`
- `get_stock_basic_tool`
- `get_daily_prices_tool`
- `get_daily_basic_tool`
- `get_stock_market_data_tool`
- `analyze_price_trend_tool`
- `generate_price_chart_tool`
- `generate_stock_charts_tool`

## Transport

Current transport:

```text
stdio
```

Not currently implemented:

```text
streamable-http
sse
```

