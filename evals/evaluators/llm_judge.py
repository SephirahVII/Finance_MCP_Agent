from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from evals.evaluators.common import research_state


JUDGE_PROMPT_PATH = Path(__file__).resolve().parents[1] / "judges" / "report_quality_judge.md"


def evaluate_llm_judge(
    result: dict[str, Any],
    expected: dict[str, Any],
    *,
    enabled: bool,
) -> dict[str, Any]:
    if not expected.get("quality"):
        return {"passed": True, "score": 1.0, "skipped": True, "reason": "no quality rubric"}
    if not enabled:
        return {"passed": True, "score": 1.0, "skipped": True, "reason": "llm judge disabled"}

    from invesagent_agent.clients.llm_client import generate_json

    state = research_state(result)
    payload = {
        "user_query": state.get("user_query") or result.get("user_query"),
        "task_plan": state.get("task_plan", {}),
        "tool_calls": state.get("tool_calls", []),
        "observations": state.get("observations", []),
        "macro_policy_analysis": state.get("macro_policy_analysis", {}),
        "final_response": result.get("final_response") or state.get("final_response"),
        "expected_quality": expected.get("quality", {}),
    }
    judge_prompt = JUDGE_PROMPT_PATH.read_text(encoding="utf-8")
    judge_result = generate_json(
        [
            {"role": "system", "content": judge_prompt},
            {
                "role": "user",
                "content": json.dumps(payload, ensure_ascii=False, default=str),
            },
        ]
    )
    overall = float(judge_result.get("overall", 0.0) or 0.0)
    min_overall = float(expected.get("quality", {}).get("min_overall", 0.0))
    return {
        "passed": overall >= min_overall,
        "score": round(overall, 4),
        "min_overall": min_overall,
        "judge_result": judge_result,
    }

