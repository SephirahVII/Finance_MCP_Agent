from __future__ import annotations

from typing import Any


def evaluate_report_quality(result: dict[str, Any], expected: dict[str, Any]) -> dict[str, Any]:
    quality = expected.get("quality", {})
    if not quality:
        return {"passed": True, "score": 1.0, "checks": []}

    response = str(result.get("final_response") or "")
    lower = response.lower()
    must_include = [str(item) for item in quality.get("must_include", [])]
    must_include_any = [str(item) for item in quality.get("must_include_any", [])]

    checks = []
    for item in must_include:
        checks.append(
            {
                "name": f"must_include:{item}",
                "passed": item.lower() in lower,
                "expected": item,
            }
        )
    if must_include_any:
        checks.append(
            {
                "name": "must_include_any",
                "passed": any(item.lower() in lower for item in must_include_any),
                "expected": must_include_any,
            }
        )

    dimensions = {
        "structure": _contains_any(lower, ("report", "summary", "analysis")),
        "risk_awareness": _contains_any(lower, ("risk", "risks", "uncertain")),
        "data_limits": _contains_any(lower, ("data limit", "data limits", "limitation")),
        "safety": _contains_any(lower, ("no investment advice", "not investment advice")),
    }
    checks.extend(
        {"name": name, "passed": passed, "expected": True}
        for name, passed in dimensions.items()
    )
    score = round(sum(1 for item in checks if item["passed"]) / max(len(checks), 1), 4)
    min_overall = float(quality.get("min_overall", 0.0))
    passed = score >= min_overall and all(
        item["passed"] for item in checks if item["name"].startswith("must_include")
    )
    return {
        "passed": passed,
        "score": score,
        "min_overall": min_overall,
        "checks": checks,
    }


def _contains_any(text: str, needles: tuple[str, ...]) -> bool:
    return any(needle in text for needle in needles)

