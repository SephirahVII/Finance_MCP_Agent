# MCP Client Configuration

This project can expose a local MCP Server over `stdio` or Streamable HTTP.

Use placeholders in the examples below and replace them with your local paths:

```text
<PYTHON_EXE>      Path to the Python executable in your project environment
<PROJECT_ROOT>    Path to the cloned project root
<TUSHARE_TOKEN>   Your local Tushare token
```

Do not commit real tokens or personal absolute paths to a public repository.

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

## Supported Transports

```text
stdio
streamable-http
```

SSE is not recommended for new work.

## Streamable HTTP

Start the MCP Server first:

```powershell
cd "<PROJECT_ROOT>"
& "<PYTHON_EXE>" -m src.mcp_server.server --transport streamable-http --host 127.0.0.1 --port 8000 --path /mcp
```

Expected startup output includes:

```text
Uvicorn running on http://127.0.0.1:8000
```

The MCP endpoint is:

```text
http://127.0.0.1:8000/mcp
```

Browser access to `/` may return `404`, and direct browser access to `/mcp` may return `406`. That is normal because MCP clients must speak the MCP protocol; the endpoint is not a normal web page.

### Cherry Studio Streamable HTTP Example

Use JSON import:

```json
{
  "mcpServers": {
    "tushareFinancialAnalystHttp": {
      "type": "streamableHttp",
      "url": "http://127.0.0.1:8000/mcp"
    }
  }
}
```

If your client uses a different type name, try:

```json
{
  "mcpServers": {
    "tushareFinancialAnalystHttp": {
      "type": "streamable-http",
      "url": "http://127.0.0.1:8000/mcp"
    }
  }
}
```

Keep Tushare credentials in the server process environment or `.env`; do not put secrets in the URL.

## stdio

`stdio` mode lets the MCP client start the Python process directly.

In stdio mode, do not start the server manually. The client launches it.

### Generic stdio Configuration

Some clients support `cwd`:

```json
{
  "mcpServers": {
    "tushareFinancialAnalyst": {
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

If the client does not support `cwd`, set `PYTHONPATH`:

```json
{
  "mcpServers": {
    "tushareFinancialAnalyst": {
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

On Windows, if a client rejects escaped backslashes in JSON, use forward slashes in paths:

```json
{
  "mcpServers": {
    "tushareFinancialAnalyst": {
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

As a fallback for Windows clients that have trouble launching Python directly, wrap the command with `cmd.exe`:

```json
{
  "mcpServers": {
    "tushareFinancialAnalyst": {
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

## Common Issues

### `ERR_CONNECTION_REFUSED`

Usually means the Streamable HTTP server is not running or the port is wrong.

Start the server and confirm:

```powershell
Test-NetConnection 127.0.0.1 -Port 8000
```

### `404 Not Found`

Accessing `http://127.0.0.1:8000/` returns `404` because the MCP endpoint is `/mcp`.

### `406 Not Acceptable`

Direct browser access to `/mcp` may return `406`. Use an MCP client rather than a browser.

### JSON import says invalid input

Check:

- JSON has no comments.
- JSON uses double quotes.
- No trailing commas.
- Windows backslashes are escaped as `\\`, or use forward slashes.
- The client supports the fields you used, such as `cwd` or `type`.

