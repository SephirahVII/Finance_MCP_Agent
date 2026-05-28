# InvesAgent Agent

LangGraph chat and investment-research workflow package for InvesAgent.

Default workflow:

```text
general_assistant
  -> general_answer
  -> investment_task_manager
      -> conditional specialist agents
```

The `General Assistant Agent` handles ordinary conversation and finance concept explanations without MCP calls. Only investment research or data-backed analysis requests are passed to the `Investment Task Manager Agent`.

Investment workflow:

```text
investment_task_manager
  -> data_collector
  -> industry_analyst          # only when required
  -> price_volume_analyst      # only when required
  -> fundamental_analyst       # only when required
  -> reviewer                  # usually for full reports
  -> report_writer             # only when a report is requested
```

This package calls the standalone MCP server through `invesagent_agent.clients.mcp_client` and does not import `invesagent_core` directly.

Key modules:

```text
agents/      LangGraph node implementations
clients/     MCP client and OpenAI-compatible LLM client
prompts/     role-specific prompts
schemas/     structured task / analyst / review outputs
workflows/   chat graph, research graph, and CLI runner
runners/     console-script entrypoints
```

Examples:

```powershell
python -m invesagent_agent.workflows.runner "你好" --show-intent
python -m invesagent_agent.workflows.runner "DCF 是什么" --show-intent
python -m invesagent_agent.workflows.runner "贵州茅台 2024-01-01 到 2024-01-31 股票价格走势怎么样" --show-intent
python -m invesagent_agent.workflows.runner "请分析泸州老窖 2022-01-01 到 2024-12-31 的量价表现和基本面" --show-intent
```

Optional multi-turn CLI history:

```powershell
python -m invesagent_agent.workflows.runner "帮我分析一下白酒行业" --history-file .invesagent_chat_history.json
python -m invesagent_agent.workflows.runner "看 2024 年，重点看量价" --history-file .invesagent_chat_history.json
```

LLM settings are optional. If no OpenAI-compatible provider is configured, workflow nodes fall back to deterministic summaries where possible.
