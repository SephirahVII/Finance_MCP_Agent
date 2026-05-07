# Finance MCP Agent

[English](README.md) | 中文

这是一个本地 MCP 金融数据分析 Agent 项目。当前版本以 Tushare 的中国 A 股 OHLCV 行情为核心，同时已经开始调整为多数据源架构，后续可以接入 AkShare、Binance 等数据源。

> 免责声明：本项目仅用于数据分析、工程实践和学习，不构成任何投资建议。

## 当前进展

项目已经从最初的 Tushare 单数据源原型，迁移到更清晰的统一架构：

```text
Agent / MCP Client
  -> MCP tools
    -> services 统一业务接口
      -> providers
        -> Tushare
        -> AkShare      # 计划中
        -> Binance      # 计划中
      -> storage cache
      -> analysis / charts / future factors
```

已经完成：

- FastMCP Server，支持 `stdio` 和 Streamable HTTP
- 统一标的解析入口
- 统一 OHLCV 行情数据模型
- Tushare A 股日线 OHLCV 数据适配
- Tushare `daily_basic` 估值数据适配，并支持权限不足的结构化错误返回
- Tushare 财务三大报表和财务指标适配
- 中国市场交易日历
- 基于 OHLCV 的基准对比分析
- 基于 OHLCV 的价格趋势分析
- 基于 OHLCV 的可配置价格图生成
- 本地 JSON 缓存工具和运行产物目录
- 可选 Agent 运行入口，支持 DeepSeek 等 OpenAI-compatible API

当前 MCP 暴露 12 个工具：

| 工具 | 作用 |
|---|---|
| `health_check` | 检查 MCP Server 是否正常运行 |
| `get_project_info` | 返回项目与运行配置摘要 |
| `resolve_instrument_tool` | 将用户输入解析为统一金融标的 |
| `get_ohlcv_tool` | 获取统一 OHLCV 行情数据 |
| `analyze_ohlcv_price_trend_tool` | 分析收益率、波动率、最大回撤、均线和极端交易日 |
| `generate_ohlcv_price_chart_tool` | 根据统一 OHLCV 数据生成可配置价格图 |
| `get_valuation_tool` | 获取统一估值和交易指标数据 |
| `analyze_valuation_tool` | 分析 PE、PB、市值、换手率和估值分位 |
| `get_trade_calendar_tool` | 获取中国市场交易日历 |
| `get_fundamentals_tool` | 获取利润表、资产负债表、现金流量表或财务指标 |
| `analyze_fundamentals_tool` | 分析盈利、成长、资产负债和现金流质量 |
| `compare_ohlcv_with_benchmark_tool` | 对比标的与基准指数的表现 |

暂未完成：

- 订单簿工具
- AkShare 数据源
- Binance 数据源
- 多 Agent 工作流
- Web 前端

## 项目结构

```text
src/
  agent/
    agent.py                 # Agent 运行入口，负责通过 MCP 调用工具
    prompts.py               # 金融分析提示词
  config/
    settings.py              # 环境变量和运行配置
  mcp_server/
    server.py                # FastMCP Server 入口
    tools_instruments.py     # 统一标的工具
    tools_market_data.py     # 统一 OHLCV、分析和图表工具
    tools_valuation.py       # 统一估值工具
    tools_fundamentals.py    # 统一财务工具
    tools_comparison.py      # 基准对比工具
  models/
    instruments.py           # 统一金融标的数据结构
    market_data.py           # OHLCV 数据结构
    analysis.py              # 价格趋势分析结果结构
    valuation.py             # 估值数据和估值分析结果结构
    fundamentals.py          # 财务报表和财务指标结构
    comparison.py            # 基准对比结果结构
    errors.py                # 通用错误结构
  providers/
    tushare/
      client.py              # Tushare client 创建
      instruments.py         # Tushare / A 股标的解析
      market_data.py         # Tushare 日线行情适配
      valuation.py           # Tushare daily_basic 适配
      fundamentals.py        # Tushare 财务报表和财务指标适配
  services/
    instruments.py           # 统一标的解析服务
    data/
      instruments.py         # 统一标的解析
      market_data.py         # OHLCV 数据源路由
      valuation.py           # 估值数据路由
      fundamentals.py        # 财务数据路由
    analysis/
      price.py               # 单标的价格分析
      valuation.py           # 估值分析
      fundamentals.py        # 基本面分析
      multivariate.py        # 基准对比和多序列分析
    metrics/
      price.py               # 价格和收益率公式
      technical.py           # 技术指标公式
      multivariate.py        # 多序列统计公式
    charts/
      price.py               # 价格图生成
  storage/
    cache.py                 # JSON 缓存读写
    paths.py                 # 运行产物路径
  utils/
    dates.py                 # 日期格式规范化
```

## 安装

推荐使用 Python 3.11+：

```powershell
conda create -n tushare-agent python=3.11 -y
conda activate tushare-agent
pip install -e . pytest ruff
```

如果不需要 editable 安装：

```powershell
pip install mcp openai openai-agents tushare pandas numpy matplotlib python-dotenv pydantic pydantic-settings pytest ruff
```

## 配置

复制 `.env.example`：

```powershell
Copy-Item .env.example .env
```

填写本地密钥：

```text
TUSHARE_TOKEN=your_tushare_token

LLM_PROVIDER=deepseek
LLM_BASE_URL=https://api.deepseek.com
LLM_MODEL=deepseek-v4-flash
DEEPSEEK_API_KEY=your_deepseek_api_key
```

不要提交 `.env`、缓存数据、图表、报告或包含个人路径的信息。

## 本地检查

检查 MCP Server 是否能创建：

```powershell
python -c "from src.mcp_server.server import create_mcp_server; print(type(create_mcp_server()).__name__)"
```

解析标的：

```powershell
python -c "from src.services.data.instruments import resolve_instrument; print(resolve_instrument('贵州茅台').to_dict())"
```

获取统一 OHLCV：

```powershell
python -c "from src.services.data.market_data import get_ohlcv; r=get_ohlcv(symbol='600519.SH', market='cn', asset_type='stock', start_date='2024-01-01', end_date='2024-01-31'); print(r.success, len(r.records), r.provider)"
```

分析价格趋势：

```powershell
python -c "from src.services.analysis.price import analyze_ohlcv_price_trend; r=analyze_ohlcv_price_trend(symbol='600519.SH', market='cn', asset_type='stock', start_date='2024-01-01', end_date='2024-01-31'); print(r.success, r.metrics.to_dict() if r.metrics else r.to_dict())"
```

获取估值数据：

```powershell
python -c "from src.services.data.valuation import get_valuation; r=get_valuation(symbol='600519.SH', market='cn', asset_type='stock', start_date='2024-01-01', end_date='2024-01-31'); print(r.success, r.error_type, len(r.records), r.message)"
```

生成包含 MA5、MA20 和成交量的 K 线图：

```powershell
python -c "from src.services.charts.price import generate_ohlcv_price_chart; r=generate_ohlcv_price_chart(symbol='600519.SH', market='cn', asset_type='stock', start_date='2024-01-01', end_date='2024-01-31', chart_type='candlestick', ma_windows='5,20', show_volume=True); print(r)"
```

分析基本面：

```powershell
python -c "from src.services.analysis.fundamentals import analyze_fundamentals; r=analyze_fundamentals(symbol='600519.SH', market='cn', asset_type='stock', start_date='2022-01-01', end_date='2024-12-31'); print(r.success, r.metrics.to_dict() if r.metrics else r.to_dict())"
```

对比个股与沪深300：

```powershell
python -c "from src.services.analysis.multivariate import compare_ohlcv_with_benchmark; r=compare_ohlcv_with_benchmark(primary_symbol='600519.SH', benchmark_symbol='000300.SH', market='cn', primary_asset_type='stock', benchmark_asset_type='index', start_date='2024-01-01', end_date='2024-12-31'); print(r.success, r.metrics.to_dict() if r.metrics else r.to_dict())"
```

运行产物会写入：

```text
data_cache/
charts/
reports/
```

这些目录已被 Git 忽略。

## 启动 MCP Server

stdio 模式：

```powershell
python -m src.mcp_server.server --transport stdio
```

直接在终端运行 stdio MCP Server 时，它会等待 MCP 客户端发送 JSON-RPC 消息，因此不显示普通交互式提示符是正常现象。

Streamable HTTP 模式：

```powershell
python -m src.mcp_server.server --transport streamable-http --host 127.0.0.1 --port 8000 --path /mcp
```

本地 MCP 地址：

```text
http://127.0.0.1:8000/mcp
```

除非你明确要部署服务并做好认证和网络控制，否则建议保持 `127.0.0.1`。

## 运行 Agent

使用默认问题：

```powershell
python -m src.agent.agent
```

使用自定义问题：

```powershell
python -m src.agent.agent "请分析贵州茅台 2024-01-01 到 2024-01-31 的价格走势，并说明收益率、波动率和最大回撤。"
```

Agent 会启动本地 MCP Server，调用工具，并输出中文分析。

## MCP 客户端配置

见 [MCP 客户端配置](docs/mcp_client_config.md)。

## 后续数据源扩展

计划中的 provider 结构：

```text
src/providers/
  tushare/
    client.py
    instruments.py
    market_data.py
    valuation.py       # daily_basic
    fundamentals.py    # 计划：财务报表 / 财务指标
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

计划中的统一服务：

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

这样可以把不同数据源的 API 差异隔离在 provider 层，让 MCP 工具始终调用稳定的统一 service。
