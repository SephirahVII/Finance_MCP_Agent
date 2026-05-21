# 旧结构迁移说明

本项目已经从早期单一 `src/` 混合结构迁移为两个顶层包：

```text
InvesAgent/
  invesagent_mcp/
  invesagent_agent/
```

## 当前结构

`invesagent_mcp` 是完整 MCP Server，内部包含金融核心：

```text
invesagent_mcp/src/
  invesagent_core/
    config/
    models/
    providers/
    services/
    storage/
    utils/

  invesagent_mcp/
    server.py
    tools/
```

`invesagent_agent` 是 LangGraph 研究工作流：

```text
invesagent_agent/src/invesagent_agent/
  agents/
  clients/
  prompts/
  schemas/
  workflows/
  runners/
  mcp_agent.py
```

## 迁移关系

| 旧路径 | 新路径 |
|---|---|
| `src/models/` | `invesagent_mcp/src/invesagent_core/models/` |
| `src/providers/` | `invesagent_mcp/src/invesagent_core/providers/` |
| `src/services/` | `invesagent_mcp/src/invesagent_core/services/` |
| `src/storage/` | `invesagent_mcp/src/invesagent_core/storage/` |
| `src/utils/` | `invesagent_mcp/src/invesagent_core/utils/` |
| `src/mcp_server/` | `invesagent_mcp/src/invesagent_mcp/` |
| `src/agents/` | `invesagent_agent/src/invesagent_agent/agents/` |
| `src/workflows/` | `invesagent_agent/src/invesagent_agent/workflows/` |

## 当前 MCP 工具

当前 MCP Server 暴露 15 个工具：

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

## 当前边界

迁移后，MCP 已经是独立子项目：

```text
MCP Client -> invesagent_mcp -> invesagent_core -> providers
```

LangGraph Agent 也通过 MCP Client 调用 MCP Server：

```text
invesagent_agent -> MCP Client -> invesagent_mcp -> invesagent_core
```

因此 Agent 侧不再直接导入 `invesagent_core`，后续前端或其他客户端也可以只接入 MCP Server 或 Agent API。
