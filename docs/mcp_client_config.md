# MCP 客户端配置

本文说明如何把 InvesAgent 的 MCP Server 接入 Cherry Studio、VS Code 或其他 MCP Client。

请用本机实际路径替换下面示例中的占位符，不要把个人真实路径提交到仓库：

```text
<PROJECT_ROOT>      InvesAgent 仓库根目录
<MCP_ROOT>          <PROJECT_ROOT>/invesagent_mcp
<PYTHON_EXE>        项目 Python 环境的 python 可执行文件
<TUSHARE_TOKEN>     你的 Tushare token
```

## 推荐方式：Streamable HTTP

HTTP 方式对 Cherry Studio 更直观。先在终端启动 MCP Server：

```powershell
cd <MCP_ROOT>
<PYTHON_EXE> -m invesagent_mcp.server --transport streamable-http --host 127.0.0.1 --port 8000 --path /mcp
```

然后在 Cherry Studio 中新增 MCP Server，选择 HTTP / Streamable HTTP，填写：

```text
http://127.0.0.1:8000/mcp
```

注意：

- 浏览器直接访问 `/mcp` 出现 `400`、`406` 或空白响应不一定代表失败，因为 MCP HTTP 端点需要 MCP Client 按协议访问。
- 如果 Cherry Studio 报 `ERR_CONNECTION_REFUSED`，通常是 MCP Server 没有启动、端口不一致，或被防火墙/代理影响。
- HTTP 方式需要保持终端中的 MCP Server 进程持续运行。

## stdio 方式

stdio 方式由 MCP Client 自动启动 Python 进程。Cherry Studio 的 JSON 导入可参考：

```json
{
  "mcpServers": {
    "invesagentFinanceMcp": {
      "command": "<PYTHON_EXE>",
      "args": [
        "-m",
        "invesagent_mcp.server",
        "--transport",
        "stdio"
      ],
      "cwd": "<MCP_ROOT>",
      "env": {
        "PYTHONPATH": "<MCP_ROOT>/src",
        "TUSHARE_TOKEN": "<TUSHARE_TOKEN>"
      }
    }
  }
}
```

Windows 路径可以使用正斜杠，例如：

```json
"cwd": "D:/path/to/InvesAgent/invesagent_mcp"
```

也可以使用双反斜杠：

```json
"cwd": "D:\\path\\to\\InvesAgent\\invesagent_mcp"
```

不要写成单反斜杠，例如 `"D:\path\..."`，这会导致 JSON 无效。

## 本地验证 MCP 工具数量

在终端执行：

```powershell
cd <PROJECT_ROOT>
<PYTHON_EXE> -c "from invesagent_mcp.server import create_mcp_server; print(type(create_mcp_server()).__name__)"
```

应输出：

```text
FastMCP
```

验证工具列表：

```powershell
cd <PROJECT_ROOT>
@'
import anyio
from invesagent_mcp.server import create_mcp_server

async def main():
    tools = await create_mcp_server().list_tools()
    print(len(tools))
    print([tool.name for tool in tools])

anyio.run(main)
'@ | <PYTHON_EXE> -
```

当前应输出 15 个工具：

```text
health_check
get_project_info
resolve_instrument_tool
get_ohlcv_tool
analyze_ohlcv_price_trend_tool
generate_ohlcv_price_chart_tool
get_trade_calendar_tool
get_valuation_tool
analyze_valuation_tool
get_fundamentals_tool
analyze_fundamentals_tool
compare_ohlcv_with_benchmark_tool
compare_ohlcv_instruments_tool
list_industries_tool
get_industry_members_tool
```

## 常见问题

### Cherry Studio HTTP 显示连接被拒绝

通常原因：

- MCP Server 没有启动；
- Cherry Studio 中填写的端口不是启动命令中的端口；
- URL 应为 `http://127.0.0.1:8000/mcp`，不要只填 `http://127.0.0.1:8000`；
- 本机代理或防火墙影响本地连接。

### Cherry Studio stdio 显示 JSON 无效

通常原因：

- JSON 中 Windows 路径使用了单反斜杠；
- JSON 顶层结构不是 `mcpServers`；
- `command` 指向的 Python 不存在；
- `cwd` 没有指向 `invesagent_mcp`；
- 未设置 `PYTHONPATH`，导致进程找不到 `invesagent_mcp` 包。

### 手动运行 stdio Server 出现 JSON-RPC 报错

这是正常现象。stdio MCP Server 不能像普通脚本一样让用户手动输入内容，它必须由 MCP Client 启动，并通过 JSON-RPC 协议通信。

### Tushare 数据为空

请检查：

```text
TUSHARE_TOKEN 是否配置
日期区间是否存在交易日或财报公告
当前 token 是否具备对应接口权限
```

