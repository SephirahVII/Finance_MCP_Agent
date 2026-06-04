from __future__ import annotations

from typing import Any


def evaluate_route(result: dict[str, Any], expected: dict[str, Any]) -> dict[str, Any]:
    expected_route = expected.get("route")
    actual_route = result.get("conversation_route")
    passed = expected_route is None or actual_route == expected_route
    return {
        "passed": passed,
        "score": 1.0 if passed else 0.0,
        "expected": expected_route,
        "actual": actual_route,
    }

