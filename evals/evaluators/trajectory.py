from __future__ import annotations

from typing import Any

from evals.evaluators.common import research_state, score_ratio


def evaluate_trajectory(result: dict[str, Any], expected: dict[str, Any]) -> dict[str, Any]:
    state = research_state(result)
    actual_agents = set(state.get("required_agents", []))
    expected_agents = set(expected.get("required_agents", []))
    forbidden_agents = set(expected.get("forbidden_agents", []))

    missing = sorted(expected_agents - actual_agents)
    forbidden_present = sorted(forbidden_agents & actual_agents)
    matched = len(expected_agents & actual_agents)
    score = score_ratio(matched, len(expected_agents))
    passed = not missing and not forbidden_present

    return {
        "passed": passed,
        "score": 0.0 if forbidden_present else score,
        "expected_agents": sorted(expected_agents),
        "actual_agents": sorted(actual_agents),
        "missing_agents": missing,
        "forbidden_agents_present": forbidden_present,
    }

