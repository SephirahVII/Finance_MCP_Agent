from __future__ import annotations

from typing import Any


def evaluate_output_quality(result: dict[str, Any], expected: dict[str, Any]) -> dict[str, Any]:
    checks = expected.get("output_checks", {})
    response = str(result.get("final_response") or "")
    if not checks:
        return {"passed": bool(response), "score": 1.0 if response else 0.0, "response": response[:300]}

    must_include = checks.get("must_include", [])
    must_include_any = checks.get("must_include_any", [])
    missing = [item for item in must_include if item.lower() not in response.lower()]
    any_passed = True
    if must_include_any:
        any_passed = any(item.lower() in response.lower() for item in must_include_any)
    passed = bool(response) and not missing and any_passed
    return {
        "passed": passed,
        "score": 1.0 if passed else 0.0,
        "missing": missing,
        "must_include_any_passed": any_passed,
        "response": response[:300],
    }

