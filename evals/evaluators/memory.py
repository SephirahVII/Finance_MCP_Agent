from __future__ import annotations

from typing import Any


def evaluate_memory(result: dict[str, Any], expected: dict[str, Any]) -> dict[str, Any]:
    expected_memory = expected.get("memory")
    if not expected_memory:
        return {"passed": True, "score": 1.0, "checks": []}

    memory = result.get("task_memory", {})
    session = memory.get("session", {}) if isinstance(memory, dict) else {}
    checks = []
    for key, expected_value in expected_memory.items():
        actual_value = session.get(key)
        if isinstance(expected_value, list):
            ok = all(item in (actual_value or []) for item in expected_value)
        else:
            ok = actual_value == expected_value
        checks.append({"name": key, "passed": ok, "expected": expected_value, "actual": actual_value})

    passed = all(item["passed"] for item in checks)
    return {
        "passed": passed,
        "score": 1.0 if passed else 0.0,
        "checks": checks,
    }

