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

`invesagent_agent` 是 LangGraph Agent 工作流：

```text
invesagent_agent/src/invesagent_agent/
  agents/
  clients/
  prompts/
  schemas/
  workflows/
  runners/
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
| `src/agent/` | `invesagent_agent/src/invesagent_agent/` |
| `src/workflows/` | `invesagent_agent/src/invesagent_agent/workflows/` |

## Agent 侧入口变化

旧版曾经存在独立的单 Agent 入口和外层 Router 文件。现在已合并为：

```text
General Assistant Agent
  -> 普通回答
  -> Investment Task Manager Agent
      -> 按需分派专业 Agent
```

当前 Agent 侧核心文件：

```text
invesagent_agent/src/invesagent_agent/agents/general_assistant.py
invesagent_agent/src/invesagent_agent/agents/investment_task_manager.py
invesagent_agent/src/invesagent_agent/workflows/chat_graph.py
invesagent_agent/src/invesagent_agent/workflows/research_graph.py
```

旧的 `intent_router.py`、`casual_chat.py`、`task_planner.py`、`mcp_agent.py` 已移除。

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

迁移后，MCP 是独立子项目：

```text
MCP Client -> invesagent_mcp -> invesagent_core -> providers
```

LangGraph Agent 通过 MCP Client 调用 MCP Server：

```text
invesagent_agent -> MCP Client -> invesagent_mcp -> invesagent_core
```

因此 Agent 侧不再直接导入 `invesagent_core`。后续前端、Cherry Studio、VS Code 或其他客户端也可以只接入 MCP Server，或者接入 Agent API。

