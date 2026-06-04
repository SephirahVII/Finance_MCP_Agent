# InvesAgent Eval Harness

This directory contains a lightweight evaluation harness for the whole
InvesAgent workspace. It evaluates the agent workflow as a system rather than
only testing individual Python functions.

## Benchmark Layers

The harness has three benchmark layers:

- **L1 deterministic workflow benchmark** (`--benchmark l1`): fast offline
  regression tests for route, planning, trajectory, tool calls, memory, RAG
  trigger behavior, and efficiency budgets. This is the default.
- **L2 integration-oriented benchmark** (`--benchmark l2`): cases shaped like
  real MCP/RAG integration checks. By default it still uses deterministic mocks;
  pass `--real-tools` and/or `--real-rag` when the local environment has the
  needed MCP server, provider tokens, cache, and Milvus data.
- **L3 quality benchmark** (`--benchmark l3`): report-quality cases with rule
  rubrics and an optional LLM-as-Judge path. Pass `--llm-judge --real-llm` to
  use the configured LLM for judging.

Run all layers:

```powershell
python evals\run_evals.py --benchmark all
```

## What It Evaluates

- Route correctness: general chat vs investment research.
- Task planning: action, target, date ranges, agents, modules, and report type.
- Agent trajectory: required and forbidden specialist agents.
- MCP tool calls: expected tools, forbidden tools, and argument checks.
- Memory behavior: multi-turn carryover and corrected user inputs.
- RAG behavior: macro/policy retrieval traces and evidence availability.
- Output quality gates: basic required phrases and generated response presence.
- Efficiency: tool call count, duplicate calls, trace steps, tool success rate,
  average latency, and max latency.
- Report quality: required report content, risk awareness, data limits, safety
  wording, and optional LLM-as-Judge scores.

## Run

From the workspace root:

```powershell
python evals\run_evals.py
```

The default mode is deterministic and does not call external LLMs, TuShare,
AKShare, or Milvus. It patches the agent runtime with mock LLM responses, uses
`EvalMockToolClient` for MCP tools, and uses fake macro/policy retrieval hits.

Useful variants:

```powershell
python evals\run_evals.py --benchmark all
python evals\run_evals.py --benchmark l2 --real-tools
python evals\run_evals.py --benchmark l3 --real-llm --llm-judge
```

Results are written to:

```text
evals/results/latest.json
evals/results/summary.md
```

## Case Files

L1 cases live under `evals/cases/*.json`.

L2 and L3 cases live under:

```text
evals/benchmarks/l2_integration/*.json
evals/benchmarks/l3_quality/*.json
```

Each case describes a user request, expected route, expected agents, expected
tools, optional argument checks, efficiency budgets, RAG requirements, and
quality rubrics.
