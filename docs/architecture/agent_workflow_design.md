# InvesAgent 多 Agent 工作流设计

## 目标

当前 Agent 侧采用两层 LangGraph：

1. 外层 `chat_graph`：处理所有用户输入，先由 General Assistant 判断本轮是否需要进入投资研究系统。
2. 内层 `research_graph`：只在确认为投资研究任务时运行，由 Investment Task Manager 规划任务并按需分派专业 Agent。

这样可以避免普通聊天、项目讨论、金融概念解释被强行送入 MCP 工具链。

## 外层 Chat Graph

```text
用户输入
  -> General Assistant Agent
    -> general_answer
    -> Investment Task Manager / research_graph
```

General Assistant 的职责：

- 只以最新一轮用户输入为主判断当前意图；
- 普通聊天、项目讨论、金融概念解释直接回答；
- 明确的投资研究、行情、基本面、行业、图表、研报任务才进入研究流程；
- 多轮历史只作为上下文，不覆盖最新输入的主要意图。

## 内层 Research Graph

```text
Investment Task Manager
  -> Data Collector
  -> Industry Analyst          # 按需
  -> Price Volume Analyst      # 按需
  -> Fundamental Analyst       # 按需
  -> Reviewer                  # 通常用于完整报告
  -> Report Writer             # 仅在需要报告时
```

Investment Task Manager 的职责：

- 假设输入已经由 General Assistant 判断为投资研究或金融数据任务；
- 基于语义理解用户的研究目标，不只依赖关键词；
- 如果信息不足，先追问标的、时间范围、分析重点或输出形式；
- 如果信息完整，生成结构化 `task_plan`；
- 在 `task_plan.required_agents` 中声明哪些专业 Agent 需要参与；
- 在 `task_plan.date_ranges` 中声明各分析模块的时间范围；
- 在 `task_plan.agent_tasks` 中给每个 Agent 分配自然语言任务说明；
- 在 `task_plan.tool_needs` 中列出每个 Agent 可能需要调用的 MCP 工具。

示例 `task_plan`：

```json
{
  "action": "execute",
  "task_type": "price_volume_analysis",
  "target": {
    "symbols": ["600519.SH"],
    "names": ["贵州茅台"],
    "industry": null,
    "market": "cn",
    "asset_type": "stock"
  },
  "start_date": "20240101",
  "end_date": "20240131",
  "date_ranges": {
    "price_volume": {
      "start_date": "20240101",
      "end_date": "20240131"
    }
  },
  "required_agents": ["data_collector", "price_volume_analyst"],
  "agent_tasks": {
    "data_collector": "解析研究对象并准备基础标的信息。",
    "price_volume_analyst": "分析价格走势、收益率、波动率和回撤，并生成图表。"
  },
  "tool_needs": {
    "data_collector": ["resolve_instrument_tool"],
    "price_volume_analyst": [
      "analyze_ohlcv_price_trend_tool",
      "generate_ohlcv_price_chart_tool"
    ]
  },
  "output_type": "analysis_summary"
}
```

如果用户没有明确时间范围，Task Manager 会按模块生成默认日期范围：

```json
{
  "date_ranges": {
    "price_volume": {
      "start_date": "最近3个月起始日",
      "end_date": "今天"
    },
    "industry": {
      "start_date": "最近3个月起始日",
      "end_date": "今天"
    },
    "fundamentals": {
      "start_date": "最近1年起始日",
      "end_date": "今天"
    },
    "valuation": {
      "start_date": "最近1年起始日",
      "end_date": "今天"
    }
  }
}
```

各专业 Agent 优先读取自己的模块日期，例如 `price_volume_analyst` 读取 `date_ranges.price_volume`，`fundamental_analyst` 读取 `date_ranges.fundamentals`。顶层 `start_date` / `end_date` 仍保留为兼容字段和整体报告范围。

## MCP 调用关系

Agent 侧不直接 import `invesagent_core`。所有真实数据获取和指标计算都通过 MCP Client 调用独立 MCP Server：

```text
Professional Agent
  -> invesagent_agent.clients.mcp_client
    -> invesagent_mcp.server
      -> invesagent_core services/providers
```

这保证 `invesagent_mcp` 可以作为独立 MCP Server 在 Cherry Studio、VS Code、Claude Desktop 或其他 MCP Client 中使用。

## 当前能力

- 普通聊天和金融概念解释不会调用工具；
- 投资任务会先生成 `task_plan`；
- Research Graph 已按 `required_agents` 条件执行，不再默认跑完整链路；
- 单纯价格走势问题只运行 Data Collector 和 Price Volume Analyst；
- 基本面问题只运行 Data Collector 和 Fundamental Analyst；
- 完整报告任务才运行 Reviewer 和 Report Writer；
- 行业研究任务会按需运行 Industry Analyst。

## 后续优化方向

- 命令行已支持通过 `--history-file` 显式保存多轮历史；后续可接入前端 session、SQLite 或用户级记忆；
- 将估值 Agent 接入 DCF、相对估值、纵向历史估值和同行比较；
- 增加宏观研究 Agent 和新闻/政策/RAG 数据源；
- 将 Report Writer 的风格、字数和输出格式做成可配置参数；
- 对 MCP 调用增加批处理和缓存策略，减少重复请求。
