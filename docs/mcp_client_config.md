# MCP 客户端配置

本项目可以通过 `stdio` 或 Streamable HTTP 暴露本地 MCP Server。

文档中的路径全部使用占位符，请替换为你自己的本地路径：

```text
<PYTHON_EXE>      项目环境中的 Python 可执行文件
<PROJECT_ROOT>    项目根目录
<TUSHARE_TOKEN>   你的本地 Tushare token
```

不要把真实 token、个人绝对路径或本机用户名提交到公开仓库。

## 当前可用工具

当前 MCP Server 暴露 6 个工具：

| 工具 | 说明 |
|---|---|
| `health_check` | 检查 MCP Server 是否正常运行 |
| `get_project_info` | 返回项目名、server 名、目录配置和 token 配置状态 |
| `resolve_instrument_tool` | 将自然语言输入、股票代码或交易对解析为统一金融标的 |
| `get_ohlcv_tool` | 获取统一 OHLCV 行情数据 |
| `analyze_ohlcv_price_trend_tool` | 基于 OHLCV 计算收益率、波动率、最大回撤、均线和极端交易日 |
| `generate_ohlcv_price_chart_tool` | 基于 OHLCV 生成价格走势图 |

旧版 `resolve_stock_code_tool`、`get_daily_prices_tool`、`analyze_price_trend_tool` 等工具已经被统一工具替代。

## 支持的传输方式

```text
stdio
streamable-http
```

新项目优先使用 `stdio` 或 Streamable HTTP。SSE 不建议作为后续主要方向。

## Streamable HTTP

先手动启动 MCP Server：

```powershell
cd "<PROJECT_ROOT>"
& "<PYTHON_EXE>" -m src.mcp_server.server --transport streamable-http --host 127.0.0.1 --port 8000 --path /mcp
```

启动成功时，终端会出现类似输出：

```text
Uvicorn running on http://127.0.0.1:8000
```

MCP endpoint 是：

```text
http://127.0.0.1:8000/mcp
```

直接用浏览器访问 `/` 返回 `404`，直接访问 `/mcp` 返回 `406` 都是正常现象。MCP endpoint 不是普通网页，需要 MCP 客户端按协议访问。

### Cherry Studio Streamable HTTP 示例

JSON 导入示例：

```json
{
  "mcpServers": {
    "financeMcpAgentHttp": {
      "type": "streamableHttp",
      "url": "http://127.0.0.1:8000/mcp"
    }
  }
}
```

如果客户端使用另一种类型命名，可以尝试：

```json
{
  "mcpServers": {
    "financeMcpAgentHttp": {
      "type": "streamable-http",
      "url": "http://127.0.0.1:8000/mcp"
    }
  }
}
```

Tushare token 建议放在服务端 `.env` 或启动进程环境变量中，不要放进 URL。

## stdio

`stdio` 模式由 MCP 客户端直接启动 Python 进程。使用 stdio 时，通常不需要你手动启动 server。

### 通用 stdio 配置

如果客户端支持 `cwd`：

```json
{
  "mcpServers": {
    "financeMcpAgent": {
      "type": "stdio",
      "command": "<PYTHON_EXE>",
      "args": [
        "-m",
        "src.mcp_server.server",
        "--transport",
        "stdio"
      ],
      "cwd": "<PROJECT_ROOT>",
      "env": {
        "TUSHARE_TOKEN": "<TUSHARE_TOKEN>"
      }
    }
  }
}
```

如果客户端不支持 `cwd`，可以设置 `PYTHONPATH`：

```json
{
  "mcpServers": {
    "financeMcpAgent": {
      "type": "stdio",
      "command": "<PYTHON_EXE>",
      "args": [
        "-m",
        "src.mcp_server.server",
        "--transport",
        "stdio"
      ],
      "env": {
        "PYTHONPATH": "<PROJECT_ROOT>",
        "TUSHARE_TOKEN": "<TUSHARE_TOKEN>"
      }
    }
  }
}
```

Windows 客户端如果不接受反斜杠路径，可以用正斜杠：

```json
{
  "mcpServers": {
    "financeMcpAgent": {
      "type": "stdio",
      "command": "C:/path/to/env/python.exe",
      "args": [
        "-m",
        "src.mcp_server.server",
        "--transport",
        "stdio"
      ],
      "env": {
        "PYTHONPATH": "D:/path/to/Finance_MCP_Agent",
        "TUSHARE_TOKEN": "<TUSHARE_TOKEN>"
      }
    }
  }
}
```

如果客户端很难直接启动 Python，可以用 `cmd.exe` 包一层：

```json
{
  "mcpServers": {
    "financeMcpAgent": {
      "type": "stdio",
      "command": "cmd.exe",
      "args": [
        "/c",
        "cd /d \"<PROJECT_ROOT>\" && \"<PYTHON_EXE>\" -m src.mcp_server.server --transport stdio"
      ],
      "env": {
        "TUSHARE_TOKEN": "<TUSHARE_TOKEN>"
      }
    }
  }
}
```

## 常见问题

### `ERR_CONNECTION_REFUSED`

通常说明 Streamable HTTP server 没有启动，或端口不一致。

检查端口：

```powershell
Test-NetConnection 127.0.0.1 -Port 8000
```

### `404 Not Found`

访问 `http://127.0.0.1:8000/` 返回 `404` 是正常的，因为 MCP endpoint 是 `/mcp`。

### `406 Not Acceptable`

直接浏览器访问 `/mcp` 可能返回 `406`，请使用 MCP 客户端连接。

### JSON 导入提示无效

检查：

- JSON 不能有注释。
- JSON 必须使用英文双引号。
- 不能有多余逗号。
- Windows 反斜杠需要写成 `\\`，或者直接使用 `/`。
- 客户端是否支持你写的字段，例如 `cwd` 或 `type`。

