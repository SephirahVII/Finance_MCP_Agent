from __future__ import annotations

import json
from typing import Any

from evals.evaluators.common import trace, tool_calls


def _call_key(call: dict[str, Any]) -> str:
    return json.dumps(
        {
            "node": call.get("node"),
            "tool": call.get("tool"),
            "arguments": call.get("arguments", {}),
        },
        ensure_ascii=False,
        sort_keys=True,
        default=str,
    )


def evaluate_efficiency(result: dict[str, Any], expected: dict[str, Any]) -> dict[str, Any]:
    budgets = expected.get("efficiency", {})
    calls = tool_calls(result)
    events = trace(result)
    observations = result.get("research_state", {}).get("observations", [])
    if not isinstance(observations, list):
        observations = []

    keys = [_call_key(call) for call in calls if isinstance(call, dict)]
    duplicate_count = len(keys) - len(set(keys))
    elapsed_values = [
        float(item.get("elapsed_ms"))
        for item in observations
        if isinstance(item, dict) and isinstance(item.get("elapsed_ms"), (int, float))
    ]
    avg_latency = round(sum(elapsed_values) / len(elapsed_values), 2) if elapsed_values else 0.0
    max_latency = round(max(elapsed_values), 2) if elapsed_values else 0.0
    success_values = [
        item.get("success")
        for item in observations
        if isinstance(item, dict) and "success" in item
    ]
    success_count = sum(1 for value in success_values if value is True)
    tool_success_rate = round(success_count / len(success_values), 4) if success_values else 1.0

    metrics = {
        "tool_call_count": len(calls),
        "duplicate_tool_call_count": duplicate_count,
        "trace_step_count": len(events),
        "avg_tool_latency_ms": avg_latency,
        "max_tool_latency_ms": max_latency,
        "tool_success_rate": tool_success_rate,
    }

    checks = []
    if "max_tool_calls" in budgets:
        checks.append(
            {
                "name": "max_tool_calls",
                "passed": metrics["tool_call_count"] <= int(budgets["max_tool_calls"]),
                "actual": metrics["tool_call_count"],
                "expected": budgets["max_tool_calls"],
            }
        )
    if "max_duplicate_tool_calls" in budgets:
        checks.append(
            {
                "name": "max_duplicate_tool_calls",
                "passed": metrics["duplicate_tool_call_count"]
                <= int(budgets["max_duplicate_tool_calls"]),
                "actual": metrics["duplicate_tool_call_count"],
                "expected": budgets["max_duplicate_tool_calls"],
            }
        )
    if "max_trace_steps" in budgets:
        checks.append(
            {
                "name": "max_trace_steps",
                "passed": metrics["trace_step_count"] <= int(budgets["max_trace_steps"]),
                "actual": metrics["trace_step_count"],
                "expected": budgets["max_trace_steps"],
            }
        )
    if "max_avg_tool_latency_ms" in budgets:
        checks.append(
            {
                "name": "max_avg_tool_latency_ms",
                "passed": metrics["avg_tool_latency_ms"] <= float(budgets["max_avg_tool_latency_ms"]),
                "actual": metrics["avg_tool_latency_ms"],
                "expected": budgets["max_avg_tool_latency_ms"],
            }
        )

    passed = all(item["passed"] for item in checks)
    return {
        "passed": passed,
        "score": 1.0 if passed else 0.0,
        "metrics": metrics,
        "checks": checks,
    }

