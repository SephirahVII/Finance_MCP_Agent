from __future__ import annotations

from typing import Any


def research_state(result: dict[str, Any]) -> dict[str, Any]:
    value = result.get("research_state")
    return value if isinstance(value, dict) else result


def run_report(result: dict[str, Any]) -> dict[str, Any]:
    rs = research_state(result)
    report = rs.get("run_report")
    if isinstance(report, dict):
        return report
    report = result.get("run_report")
    return report if isinstance(report, dict) else {}


def tool_calls(result: dict[str, Any]) -> list[dict[str, Any]]:
    calls = research_state(result).get("tool_calls", [])
    return calls if isinstance(calls, list) else []


def trace(result: dict[str, Any]) -> list[dict[str, Any]]:
    value = research_state(result).get("trace", result.get("trace", []))
    return value if isinstance(value, list) else []


def score_ratio(matches: int, total: int) -> float:
    if total <= 0:
        return 1.0
    return round(matches / total, 4)

