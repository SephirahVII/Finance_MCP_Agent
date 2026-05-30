from __future__ import annotations

from typing import Any


def default_analysis(
    summary: str,
    key_findings: list[str] | None = None,
    risks: list[str] | None = None,
    data_limits: list[str] | None = None,
    confidence: str = "low",
) -> dict[str, Any]:
    return {
        "summary": summary,
        "key_findings": key_findings or [],
        "strengths": [],
        "risks": risks or [],
        "data_limits": data_limits or [],
        "confidence": confidence,
        "reasoning_summary": key_findings or [],
    }


def get_module_date_range(state: dict[str, Any], module: str) -> tuple[str, str]:
    """Return a module-specific date range with legacy top-level fallback."""
    date_ranges = state.get("date_ranges", {})
    module_range = date_ranges.get(module, {}) if isinstance(date_ranges, dict) else {}
    if not isinstance(module_range, dict):
        module_range = {}
    start_date = module_range.get("start_date") or state.get("start_date", "")
    end_date = module_range.get("end_date") or state.get("end_date", "")
    return str(start_date or ""), str(end_date or "")
