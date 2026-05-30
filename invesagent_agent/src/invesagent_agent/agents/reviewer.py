from __future__ import annotations

from invesagent_agent.prompts.reviewer import REVIEWER_PROMPT
from invesagent_agent.runtime.agent_runtime import AgentRuntime
from invesagent_agent.workflows.research_state import ResearchState


def run_reviewer(state: ResearchState) -> ResearchState:
    """Review collected research material before final report writing."""
    runtime = AgentRuntime(state, "reviewer")
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
    review = runtime.call_llm_json(
        system_prompt=REVIEWER_PROMPT,
        context=runtime.context({"warnings": warnings}),
        fallback=fallback,
    )

    review_comments = []
    review_comments.extend(review.get("issues", []))
    review_comments.extend(review.get("missing_data", []))
    review_comments.extend(review.get("unsupported_claims", []))

    return runtime.finish(
        {
            "reflection": review,
            "review_comments": review_comments,
            "reasoning_summary": {
                **state.get("reasoning_summary", {}),
                "reviewer": [review.get("summary", "")],
            },
        }
    )
