# InvesAgent Agent

LangGraph research workflow package for InvesAgent.

Current workflow:

```text
task_planner -> data_collector -> industry_analyst -> price_volume_analyst -> fundamental_analyst -> reviewer -> report_writer
```

This package is the Agent side of the project. It calls the standalone MCP server through `invesagent_agent.clients.mcp_client` and does not import `invesagent_core` directly.

Key modules:

```text
agents/      LangGraph node implementations
clients/     MCP client and OpenAI-compatible LLM client
prompts/     role-specific prompts
schemas/     structured task / analyst / review outputs
workflows/   graph definition and CLI runner
runners/     console-script entrypoints
```

Run a company research workflow:

```powershell
python -m invesagent_agent.workflows.runner "请分析泸州老窖 2022-01-01 到 2024-12-31 的量价表现和基本面" --industry-member-limit 3
```

Run an industry research workflow:

```powershell
python -m invesagent_agent.workflows.runner "请分析白酒行业 2024-01-01 到 2024-01-31 的主要公司量价表现和基本面" --industry-member-limit 3
```

LLM settings are optional. If no OpenAI-compatible provider is configured, workflow nodes fall back to deterministic summaries where possible.
