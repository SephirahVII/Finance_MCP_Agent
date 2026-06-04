from __future__ import annotations

from typing import Any

from evals.evaluators.common import score_ratio, tool_calls


def evaluate_tool_calls(result: dict[str, Any], expected: dict[str, Any]) -> dict[str, Any]:
    calls = tool_calls(result)
    actual_tools = [str(call.get("tool")) for call in calls if isinstance(call, dict)]
    actual_set = set(actual_tools)

    if expected.get("forbidden_tools"):
        passed = not actual_tools
        return {
            "passed": passed,
            "score": 1.0 if passed else 0.0,
            "actual_tools": actual_tools,
            "unexpected_tools": actual_tools,
        }

    expected_tools = set(expected.get("tools", []))
    missing = sorted(expected_tools - actual_set)
    matched = len(expected_tools & actual_set)
    redundant = [tool for tool in actual_tools if tool not in expected_tools]
    passed = not missing

    return {
        "passed": passed,
        "score": score_ratio(matched, len(expected_tools)),
        "expected_tools": sorted(expected_tools),
        "actual_tools": actual_tools,
        "missing_tools": missing,
        "redundant_tools": redundant,
    }

