from __future__ import annotations

from typing import Any

from evals.evaluators.common import research_state, trace


def evaluate_rag(result: dict[str, Any], expected: dict[str, Any]) -> dict[str, Any]:
    expected_rag = expected.get("rag")
    if not expected_rag:
        return {"passed": True, "score": 1.0, "checks": []}

    state = research_state(result)
    macro = state.get("macro_policy_analysis", {})
    raw = macro.get("raw", {}) if isinstance(macro, dict) else {}
    hits = raw.get("hits", []) if isinstance(raw, dict) else []
    completed = [
        item for item in trace(result)
        if item.get("event") == "rag_completed" and item.get("node") == "macro_policy_analyst"
    ]
    min_hits = int(expected_rag.get("min_hits", 0))
    source_type = expected_rag.get("source_type")

    checks = [
        {"name": "min_hits", "passed": len(hits) >= min_hits, "actual": len(hits), "expected": min_hits},
        {
            "name": "source_type",
            "passed": source_type is None or raw.get("source_type") == source_type,
            "actual": raw.get("source_type"),
            "expected": source_type,
        },
        {"name": "rag_completed_trace", "passed": bool(completed), "actual": len(completed), "expected": 1},
    ]
    passed = all(item["passed"] for item in checks)
    return {"passed": passed, "score": 1.0 if passed else 0.0, "checks": checks}

