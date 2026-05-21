# MCP 客户端配置

本文说明如何把 InvesAgent 的 MCP Server 接入 Cherry Studio、VS Code 或其他 MCP Client。

请用占位路径替换下面示例中的内容，不要把个人真实路径提交到仓库：

```text
<PROJECT_ROOT>      InvesAgent 仓库根目录
<PYTHON_EXE>        Python 可执行文件，通常来自你的项目环境
<TUSHARE_TOKEN>     你的 Tushare token
```

## Streamable HTTP

先在终端启动 MCP Server：

```powershell
cd <PROJECT_ROOT>/invesagent_mcp
<PYTHON_EXE> -m invesagent_mcp.server --transport streamable-http --host 127.0.0.1 --port 8000 --path /mcp
```

客户端 URL：

```text
http://127.0.0.1:8000/mcp
```

HTTP 方式适合 Cherry Studio、支持远程 URL 的 MCP Client，以及后续前端或服务化部署。

## stdio

stdio 配置示例：

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
      "cwd": "<PROJECT_ROOT>/invesagent_mcp",
      "env": {
        "TUSHARE_TOKEN": "<TUSHARE_TOKEN>"
      }
    }
  }
}
```

如果使用 Windows 路径，JSON 中的反斜杠需要写成双反斜杠，或者使用正斜杠。

## 验证工具列表

在本地验证 MCP Server 是否能暴露工具：

```powershell
cd <PROJECT_ROOT>/invesagent_mcp
<PYTHON_EXE> -c "import anyio; from invesagent_mcp.server import create_mcp_server; exec('async def main():\n    tools = await create_mcp_server().list_tools()\n    print(len(tools))\n    print([t.name for t in tools])'); anyio.run(main)"
```

当前应输出 15 个工具。

## 常见问题

如果 HTTP 方式提示连接被拒绝，通常是 MCP Server 没有启动，或者客户端 URL、端口、路径不一致。

如果 stdio 方式提示 JSON 无效，不要在终端手动输入内容给 stdio MCP Server。stdio MCP Server 需要由 MCP Client 启动，并通过 JSON-RPC 通信。

如果 Tushare 数据返回为空，先确认：

```text
TUSHARE_TOKEN 是否配置
日期区间是否存在交易日或财报公告
当前 token 是否具备对应接口权限
```
