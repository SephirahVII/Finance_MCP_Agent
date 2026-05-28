from __future__ import annotations

from invesagent_agent.agents.base import run_llm_json_node
from invesagent_agent.prompts.reviewer import REVIEWER_PROMPT
from invesagent_agent.workflows.research_state import ResearchState


def run_reviewer(state: ResearchState) -> ResearchState:
    """Review collected research material before final report writing."""
    warnings = list(state.get("warnings", []))
    fallback = {
        "status": "ok",
        "summary": "完成基础审查；LLM 审查不可用时采用保守通过。",
        "issues": [],
        "missing_data": [],
        "unsupported_claims": [],
        "recommended_next_steps": [],
        "data_limits": warnings[-10:],
    }
    review = run_llm_json_node(
        system_prompt=REVIEWER_PROMPT,
        context={
            "user_query": state.get("user_query", ""),
            "task_plan": state.get("task_plan", {}),
            "observations": state.get("observations", []),
            "analyst_notes": state.get("analyst_notes", {}),
            "price_volume_analysis": state.get("price_volume_analysis", {}),
            "fundamental_analysis": state.get("fundamental_analysis", {}),
            "industry_analysis": state.get("industry_analysis", {}),
            "warnings": warnings,
        },
        fallback=fallback,
        role="reviewer",
        memory=state.get("task_memory", {}),
        warnings=warnings,
    )

    review_comments = []
    review_comments.extend(review.get("issues", []))
    review_comments.extend(review.get("missing_data", []))
    review_comments.extend(review.get("unsupported_claims", []))

    return {
        **state,
        "reflection": review,
        "review_comments": review_comments,
        "reasoning_summary": {
            **state.get("reasoning_summary", {}),
            "reviewer": [review.get("summary", "")],
        },
        "warnings": warnings,
    }
