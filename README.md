# Finance MCP Agent

English | [中文](README.zh-CN.md)

A local MCP-powered financial data analysis agent. The current implementation focuses on Chinese A-share OHLCV data through Tushare, while the codebase is being shaped for multiple data providers such as AkShare and Binance.

> Disclaimer: This project is for data analysis, engineering practice, and learning. It does not provide investment advice.

## Current Status

The project has moved from a Tushare-only prototype to a unified provider/service architecture.

Implemented:

- FastMCP server with `stdio` and Streamable HTTP transports
- Unified instrument resolution
- Unified OHLCV market data model
- Tushare provider for China A-share daily OHLCV data
- Tushare `daily_basic` valuation adapter with structured permission handling
- Tushare fundamentals adapter for income, balance sheet, cashflow, and financial indicators
- China market trade calendar
- Benchmark comparison for OHLCV return, volatility, drawdown, and correlation
- Price trend analysis based on OHLCV data
- Configurable price chart generation
- Local JSON cache helpers and runtime output directories
- Optional Agent runner with OpenAI-compatible LLM providers such as DeepSeek

Currently exposed MCP tools:

| Tool | Purpose |
|---|---|
| `health_check` | Check whether the MCP server is running |
| `get_project_info` | Return project and runtime configuration metadata |
| `resolve_instrument_tool` | Resolve user input into a unified financial instrument |
| `get_ohlcv_tool` | Fetch unified OHLCV data |
| `analyze_ohlcv_price_trend_tool` | Analyze return, volatility, drawdown, moving averages, and extreme days |
| `generate_ohlcv_price_chart_tool` | Generate a configurable price chart from unified OHLCV data |
| `get_valuation_tool` | Fetch unified valuation and trading-metric data |
| `analyze_valuation_tool` | Analyze PE, PB, market value, turnover, and valuation percentiles |
| `get_trade_calendar_tool` | Fetch China market trading calendar records |
| `get_fundamentals_tool` | Fetch income, balance sheet, cashflow, or financial indicator data |
| `analyze_fundamentals_tool` | Analyze profitability, growth, balance sheet, and cashflow quality |
| `compare_ohlcv_with_benchmark_tool` | Compare one instrument with a benchmark |

Not implemented yet:

- Order book tools
- AkShare provider
- Binance provider
- Multi-agent workflow
- Web frontend

## Architecture

```text
Agent / MCP Client
  -> MCP tools
    -> services unified API
      -> providers
        -> Tushare
        -> AkShare      # planned
        -> Binance      # planned
      -> storage cache
      -> analysis / charts / future factors
```

Current source layout:

```text
src/
  agent/
    agent.py                 # Agent runner using MCP tools
    prompts.py               # Financial analysis instructions
  config/
    settings.py              # Environment and runtime settings
  mcp_server/
    server.py                # FastMCP server entrypoint
    tools_instruments.py     # Unified instrument tools
    tools_market_data.py     # Unified OHLCV, analysis, and chart tools
    tools_valuation.py       # Unified valuation tools
    tools_fundamentals.py    # Unified fundamentals tools
    tools_comparison.py      # Benchmark comparison tools
  models/
    instruments.py           # Unified financial instrument model
    market_data.py           # OHLCV data models
    analysis.py              # Price trend analysis result models
    valuation.py             # Valuation data and analysis result models
    fundamentals.py          # Financial statement and indicator models
    comparison.py            # Benchmark comparison result models
    errors.py                # Shared error models
  providers/
    tushare/
      client.py              # Tushare client creation
      instruments.py         # Tushare / China A-share instrument resolution
      market_data.py         # Tushare daily data adapter
      valuation.py           # Tushare daily_basic adapter
      fundamentals.py        # Tushare financial statements and indicators
  services/
    instruments.py           # Unified instrument resolution service
    data/
      instruments.py         # Unified instrument resolution
      market_data.py         # Provider routing for OHLCV data
      valuation.py           # Valuation data routing
      fundamentals.py        # Fundamentals data routing
    analysis/
      price.py               # Single-instrument OHLCV analysis
      valuation.py           # Valuation analysis
      fundamentals.py        # Fundamentals analysis
      multivariate.py        # Benchmark and multi-series analysis
    metrics/
      price.py               # Price and return formulas
      technical.py           # Technical indicator formulas
      multivariate.py        # Cross-series formulas
    charts/
      price.py               # Price chart generation
  storage/
    cache.py                 # JSON cache helpers
    paths.py                 # Runtime output paths
  utils/
    dates.py                 # Date normalization helpers
```

## Requirements

- Python 3.11+
- Tushare Pro token
- Optional: OpenAI-compatible LLM API key for Agent mode

Install dependencies:

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

Fill in local secrets:

```text
TUSHARE_TOKEN=your_tushare_token

LLM_PROVIDER=deepseek
LLM_BASE_URL=https://api.deepseek.com
LLM_MODEL=deepseek-v4-flash
DEEPSEEK_API_KEY=your_deepseek_api_key
```

Do not commit `.env`, generated charts, cached data, reports, or personal absolute paths.

## Smoke Checks

Check the MCP server object:

```powershell
python -c "from src.mcp_server.server import create_mcp_server; print(type(create_mcp_server()).__name__)"
```

Resolve an instrument:

```powershell
python -c "from src.services.data.instruments import resolve_instrument; print(resolve_instrument('贵州茅台').to_dict())"
```

Fetch unified OHLCV data:

```powershell
python -c "from src.services.data.market_data import get_ohlcv; r=get_ohlcv(symbol='600519.SH', market='cn', asset_type='stock', start_date='2024-01-01', end_date='2024-01-31'); print(r.success, len(r.records), r.provider)"
```

Analyze price trend:

```powershell
python -c "from src.services.analysis.price import analyze_ohlcv_price_trend; r=analyze_ohlcv_price_trend(symbol='600519.SH', market='cn', asset_type='stock', start_date='2024-01-01', end_date='2024-01-31'); print(r.success, r.metrics.to_dict() if r.metrics else r.to_dict())"
```

Fetch valuation data:

```powershell
python -c "from src.services.data.valuation import get_valuation; r=get_valuation(symbol='600519.SH', market='cn', asset_type='stock', start_date='2024-01-01', end_date='2024-01-31'); print(r.success, r.error_type, len(r.records), r.message)"
```

Generate a candlestick chart with MA5, MA20, and volume:

```powershell
python -c "from src.services.charts.price import generate_ohlcv_price_chart; r=generate_ohlcv_price_chart(symbol='600519.SH', market='cn', asset_type='stock', start_date='2024-01-01', end_date='2024-01-31', chart_type='candlestick', ma_windows='5,20', show_volume=True); print(r)"
```

Analyze fundamentals:

```powershell
python -c "from src.services.analysis.fundamentals import analyze_fundamentals; r=analyze_fundamentals(symbol='600519.SH', market='cn', asset_type='stock', start_date='2022-01-01', end_date='2024-12-31'); print(r.success, r.metrics.to_dict() if r.metrics else r.to_dict())"
```

Compare a stock with CSI 300:

```powershell
python -c "from src.services.analysis.multivariate import compare_ohlcv_with_benchmark; r=compare_ohlcv_with_benchmark(primary_symbol='600519.SH', benchmark_symbol='000300.SH', market='cn', primary_asset_type='stock', benchmark_asset_type='index', start_date='2024-01-01', end_date='2024-12-31'); print(r.success, r.metrics.to_dict() if r.metrics else r.to_dict())"
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
python -m src.mcp_server.server --transport stdio
```

When run directly in a terminal, a `stdio` MCP server waits for JSON-RPC messages from an MCP client. It is normal for it not to behave like an interactive shell.

Run with Streamable HTTP transport:

```powershell
python -m src.mcp_server.server --transport streamable-http --host 127.0.0.1 --port 8000 --path /mcp
```

The local MCP endpoint is:

```text
http://127.0.0.1:8000/mcp
```

Keep the host as `127.0.0.1` unless you intentionally deploy the service with proper authentication and network controls.

## Run Agent

Run with the default query:

```powershell
python -m src.agent.agent
```

Run with a custom query:

```powershell
python -m src.agent.agent "请分析贵州茅台 2024-01-01 到 2024-01-31 的价格走势，并说明收益率、波动率和最大回撤。"
```

The Agent starts a local MCP server, calls the available tools, and writes the final analysis in Chinese.

## MCP Client Integration

See [MCP client configuration](docs/mcp_client_config.md).

## Future Provider Expansion

Planned provider layout:

```text
src/providers/
  tushare/
    client.py
    instruments.py
    market_data.py
    valuation.py       # daily_basic adapter
    fundamentals.py    # planned statements / financial indicators
  akshare/
    client.py
    instruments.py
    market_data.py
    valuation.py
    futures.py
  binance/
    client.py
    instruments.py
    market_data.py     # klines
    order_book.py      # bids / asks / depth
```

Planned unified services:

```text
src/services/
  data/valuation.py
  data/fundamentals.py
  analysis/valuation.py
  analysis/fundamentals.py
  unified_order_book.py
  analysis_dataset.py
  factors.py
```

This keeps provider-specific APIs isolated and lets MCP tools call stable unified services.
