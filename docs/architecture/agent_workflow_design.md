# InvesAgent 多 Agent 工作流设计

## 目标

当前项目把事实数据、分析工具、LLM 解释和工作流编排拆开：

- `invesagent_mcp` 提供真实数据、分析计算、图表生成和 MCP 工具。
- `invesagent_agent.clients` 负责连接 MCP Server 与 OpenAI-compatible LLM。
- `invesagent_agent.agents` 存放各个角色 Agent 的 LangGraph 节点。
- `invesagent_agent.prompts` 存放每个角色的独立提示词。
- `invesagent_agent.workflows` 使用 LangGraph 串联整个研究流程。

## 执行路径

```text
用户问题
  -> research_graph
    -> task_planner
    -> data_collector
    -> industry_analyst
    -> price_volume_analyst
    -> fundamental_analyst
    -> reviewer
    -> report_writer
```

数据仍然来自 MCP：

```text
Agent 节点
  -> clients.mcp_client
    -> invesagent_mcp.server
      -> invesagent_core services/providers
```

LLM 解释发生在事实工具调用之后：

```text
MCP 原始结果
  -> 压缩后的 JSON 上下文
  -> 角色提示词
  -> LLM 结构化输出
  -> ResearchState 中的 analyst_notes / reasoning_summary / reflection
```

## 可见推理信息

工作流保存的是可展示的分析摘要，而不是隐藏思维链：

- `analyst_notes`：各角色的结构化分析结论。
- `reasoning_summary`：面向用户的简短分析依据。
- `reflection`：结果审查节点给出的审查意见。
- `tool_calls`：工作流请求过的 MCP 工具调用记录。
- `observations`：工具结果的压缩摘要。

## 降级行为

LLM 调用是可选能力。如果没有安装依赖、没有配置 API key、网络不可用或 provider 不可用，节点会降级为确定性摘要并追加 warning。这样项目既可以在本地数据工具模式下运行，也可以在配置 LLM 后获得更强的分析和写作能力。

## 扩展方式

新增一个 LLM 节点通常需要：

1. 在 `invesagent_agent/prompts/` 下新增角色提示词。
2. 如有需要，在 `invesagent_agent/schemas/` 下新增结构化输出定义。
3. 在 `invesagent_agent/agents/` 下新增节点函数。
4. 在 `workflows/research_graph.py` 中注册节点与边。

推荐节点模式：

```text
收集 MCP 事实
  -> 构造紧凑上下文
  -> 调用 LLM JSON/text 节点
  -> 将原始数据与分析结论写回 state
```
