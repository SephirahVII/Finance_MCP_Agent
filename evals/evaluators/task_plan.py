from __future__ import annotations

from typing import Any

from evals.evaluators.common import research_state, score_ratio


def evaluate_task_plan(result: dict[str, Any], expected: dict[str, Any]) -> dict[str, Any]:
    state = research_state(result)
    plan = state.get("task_plan", {}) if isinstance(state.get("task_plan"), dict) else {}
    checks = []

    if expected.get("action") is not None:
        checks.append(("action", plan.get("action") == expected.get("action")))
    if expected.get("report_type") is not None:
        checks.append(("report_type", plan.get("report_type") == expected.get("report_type")))
    params = expected.get("params", {})
    if "symbol" in params:
        symbols = plan.get("target", {}).get("symbols", [])
        checks.append(("symbol", params["symbol"] in symbols or params["symbol"] in state.get("symbols", [])))
    if "start_date" in params:
        checks.append(("start_date", state.get("start_date") == params["start_date"]))
    if "end_date" in params:
        checks.append(("end_date", state.get("end_date") == params["end_date"]))

    passed_count = sum(1 for _, ok in checks if ok)
    passed = passed_count == len(checks)
    return {
        "passed": passed,
        "score": score_ratio(passed_count, len(checks)),
        "checks": [{"name": name, "passed": ok} for name, ok in checks],
        "task_plan": plan,
    }

