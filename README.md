# Tushare AI Financial Agent

A local MCP-powered financial analysis agent for Chinese A-share market data.

This project provides a local MCP Server that wraps Tushare data access, price-trend analysis, chart generation, and an optional LLM Agent interface. It is designed for personal research, reproducible local workflows, and integration with MCP-compatible clients.

> Disclaimer: This project is for data analysis and learning purposes only. It does not provide investment advice.

## Features

- Local MCP Server over `stdio`
- Tushare Pro stock-name and stock-code resolution
- Daily OHLCV data retrieval
- Local JSON cache for daily market data
- Graceful handling of Tushare permission, rate-limit, empty-data, and network errors
- Price trend analysis:
  - interval return
  - annualized volatility
  - maximum drawdown
  - MA5 / MA20 / MA60
  - highest / lowest price
  - largest up / down trading day
- Price chart generation with Close, MA5, and MA20
- Optional Agent runner using OpenAI-compatible providers such as DeepSeek

## Current Scope

Implemented:

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

Not included yet:

- Web frontend
- Multi-agent workflow
- Fundamental statement analysis
- Markdown/PDF report generator

The current design intentionally keeps report writing in the Agent layer. The MCP Server provides structured data, analysis metrics, and chart paths.

## Requirements

- Python 3.11+
- Tushare Pro token
- Optional: OpenAI-compatible LLM API key for Agent mode

Recommended Conda environment:

```powershell
conda create -n tushare-agent python=3.11 -y
conda activate tushare-agent
pip install -e . pytest ruff
```

If editable installation is not needed:

```powershell
pip install mcp openai openai-agents tushare pandas numpy matplotlib python-dotenv pydantic pydantic-settings pytest ruff
```

## Configuration

Copy `.env.example` to `.env`:

```powershell
Copy-Item .env.example .env
```

Then fill in local secrets:

```text
TUSHARE_TOKEN=your_tushare_token

LLM_PROVIDER=deepseek
LLM_BASE_URL=https://api.deepseek.com
LLM_MODEL=deepseek-v4-flash
DEEPSEEK_API_KEY=your_deepseek_api_key
```

Do not commit `.env`.

`MCP_PYTHON_PATH` is optional. If omitted, the Agent uses the Python interpreter that launched `src.agent.agent`.

## Run Local Smoke Checks

Check core tools without starting an MCP client:

```powershell
python -c "from src.mcp_server.server import health_check, get_project_info; print(health_check()); print(get_project_info())"
```

Check stock resolution:

```powershell
python -c "from src.services.stock_resolver import resolve_stock_code; print(resolve_stock_code('600519.SH'))"
```

Check daily market data:

```powershell
python -c "from src.services.market_data import get_daily_prices; print(get_daily_prices('600519.SH','2024-01-01','2024-01-31', limit=3))"
```

Check price analysis:

```powershell
python -c "from src.services.analyzer import analyze_price_trend; print(analyze_price_trend('600519.SH','2024-01-01','2024-01-31'))"
```

Generate a chart:

```powershell
python -c "from src.services.chart_generator import generate_price_chart; print(generate_price_chart('600519.SH','2024-01-01','2024-01-31'))"
```

Generated runtime files are written under:

```text
data_cache/
charts/
reports/
```

These directories are ignored by Git.

## Run MCP Server

Run with local `stdio` transport:

```powershell
python -m src.mcp_server.server
```

or explicitly:

```powershell
python -m src.mcp_server.server --transport stdio
```

When run directly in a terminal, a `stdio` MCP Server waits for JSON-RPC messages from an MCP client. It is normal for it not to print a normal interactive prompt.

Run with Streamable HTTP transport:

```powershell
python -m src.mcp_server.server --transport streamable-http --host 127.0.0.1 --port 8000 --path /mcp
```

The local HTTP endpoint is:

```text
http://127.0.0.1:8000/mcp
```

For safety, keep the host as `127.0.0.1` unless you are intentionally deploying the service with proper authentication and network controls.

## Run Agent

Run with the default query:

```powershell
python -m src.agent.agent
```

Run with a custom query:

```powershell
python -m src.agent.agent "请分析贵州茅台 2024-01-01 到 2024-01-31 的价格走势，说明收益率、波动率、最大回撤，并生成图表"
```

The Agent starts the local MCP Server, calls the available tools, and writes the final analysis in Chinese.

## MCP Client Integration

See [MCP client configuration](docs/mcp_client_config.md).

## Project Structure

```text
src/
  agent/
    agent.py          # Agent runner using MCP tools
    prompts.py        # Financial analyst instructions
  config/
    settings.py       # Environment and runtime settings
  mcp_server/
    server.py         # FastMCP server entrypoint
    tools_stock.py    # Stock and market-data tools
    tools_analysis.py # Price analysis tools
    tools_chart.py    # Chart generation tools
  services/
    tushare_client.py # Tushare Pro client creation
    stock_resolver.py # Stock name/code resolution
    market_data.py    # Daily and daily_basic data access
    analyzer.py       # Price trend analysis
    chart_generator.py# Matplotlib chart generation
  storage/
    cache.py          # JSON cache helpers
    paths.py          # Runtime output paths
```

## Notes

- `daily_basic` may require higher Tushare permissions. The tool returns a structured `permission_denied` result if unavailable.
- `stock_basic` has strict frequency limits, so caching is recommended.
- Large raw market data should be processed locally and summarized before being sent to an LLM to control token usage.
