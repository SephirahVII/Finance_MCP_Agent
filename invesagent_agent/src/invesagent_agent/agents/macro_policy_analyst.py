from __future__ import annotations

import re
from typing import Any

from invesagent_agent.agents.base import default_analysis, get_module_date_range
from invesagent_agent.prompts.macro_policy_analyst import MACRO_POLICY_ANALYST_PROMPT
from invesagent_agent.runtime.agent_runtime import AgentRuntime
from invesagent_agent.workflows.research_state import ResearchState


def _year(value: str | None) -> int | None:
    if not value:
        return None
    match = re.match(r"(\d{4})", str(value))
    return int(match.group(1)) if match else None


def _hit_to_dict(hit: Any) -> dict[str, Any]:
    return {
        "chunk_id": getattr(hit, "chunk_id", ""),
        "doc_id": getattr(hit, "doc_id", ""),
        "title": getattr(hit, "title", ""),
        "source_type": getattr(hit, "source_type", ""),
        "source_name": getattr(hit, "source_name", ""),
        "jurisdiction_level": getattr(hit, "jurisdiction_level", ""),
        "region": getattr(hit, "region", ""),
        "year": getattr(hit, "year", None),
        "source_path": getattr(hit, "source_path", ""),
        "topics": list(getattr(hit, "topics", []) or []),
        "content_categories": list(getattr(hit, "content_categories", []) or []),
        "policy_tools": list(getattr(hit, "policy_tools", []) or []),
        "mentioned_industries": list(getattr(hit, "mentioned_industries", []) or []),
        "score": getattr(hit, "score", None),
        "dense_score": getattr(hit, "dense_score", None),
        "bm25_score": getattr(hit, "bm25_score", None),
        "retrieval_method": getattr(hit, "retrieval_method", ""),
        "text": (getattr(hit, "text", "") or "")[:1200],
    }


def _retrieve_policy_evidence(
    query: str,
    *,
    start_year: int | None,
    end_year: int | None,
    top_k: int = 6,
) -> tuple[list[dict[str, Any]], list[str], str]:
    warnings: list[str] = []
    try:
        from invesagent_rag import RagRetriever
    except Exception as exc:
        return [], [f"macro_policy_analyst：invesagent_rag 不可用：{exc}"], "unavailable"

    retriever = RagRetriever()
    try:
        hits = retriever.retrieve_policy(
            query,
            start_year=start_year,
            end_year=end_year,
            top_k=top_k,
            mode="dense",
        )
        return [_hit_to_dict(hit) for hit in hits], warnings, "dense"
    except Exception as exc:
        warnings.append(f"macro_policy_analyst：dense RAG 检索失败：{exc}")

    try:
        hits = retriever.retrieve_policy(
            query,
            start_year=start_year,
            end_year=end_year,
            top_k=top_k,
            mode="bm25",
        )
        return [_hit_to_dict(hit) for hit in hits], warnings, "bm25"
    except Exception as exc:
        warnings.append(f"macro_policy_analyst：bm25 RAG 检索失败：{exc}")
        return [], warnings, "failed"


def run_macro_policy_analyst(state: ResearchState) -> ResearchState:
    """Retrieve macro/policy evidence through invesagent_rag and analyze it."""
    runtime = AgentRuntime(state, "macro_policy_analyst")
    query = state.get("user_query", "")
    start_date, end_date = get_module_date_range(state, "macro_policy")
    start_year = _year(start_date)
    end_year = _year(end_date)

    runtime.trace(
        "rag_requested",
        {
            "source_type": "macro_policy",
            "start_year": start_year,
            "end_year": end_year,
            "top_k": 6,
        },
    )
    evidence, retrieval_warnings, retrieval_mode = _retrieve_policy_evidence(
        query,
        start_year=start_year,
        end_year=end_year,
        top_k=6,
    )
    warnings = list(state.get("warnings", []))
    warnings.extend(retrieval_warnings)
    state["warnings"] = warnings
    runtime.trace(
        "rag_completed",
        {
            "source_type": "macro_policy",
            "mode": retrieval_mode,
            "hit_count": len(evidence),
        },
    )

    raw = {
        "query": query,
        "source_type": "macro_policy",
        "retrieval_mode": retrieval_mode,
        "date_range": {"start_date": start_date, "end_date": end_date},
        "year_filter": {"start_year": start_year, "end_year": end_year},
        "hits": evidence,
    }
    fallback = default_analysis(
        summary="宏观/政策检索已完成，但 LLM 解读不可用。",
        key_findings=[
            f"通过 {retrieval_mode} 检索到 {len(evidence)} 条宏观/政策证据片段。"
        ],
        data_limits=(
            ["未检索到宏观/政策证据。"] if not evidence else []
        )
        + retrieval_warnings,
        confidence="medium" if evidence else "low",
    )
    if evidence:
        fallback["citations"] = [
            f"{item.get('title') or item.get('source_name')} ({item.get('year')}, {item.get('chunk_id')})"
            for item in evidence[:5]
        ]

    analysis = runtime.call_llm_json(
        system_prompt=MACRO_POLICY_ANALYST_PROMPT,
        context=runtime.context({"raw": raw}),
        fallback=fallback,
    )
    final_response = analysis.get("summary") or fallback["summary"]
    findings = analysis.get("key_findings", [])
    if findings:
        final_response = "\n".join([final_response, *[f"- {item}" for item in findings[:5]]])

    return runtime.finish(
        {
            "macro_policy_analysis": {
                "raw": raw,
                "analysis": analysis,
                "date_range": raw["date_range"],
            },
            "analyst_notes": {
                **state.get("analyst_notes", {}),
                "macro_policy": analysis,
            },
            "reasoning_summary": {
                **state.get("reasoning_summary", {}),
                "macro_policy": analysis.get("reasoning_summary", []),
            },
            "warnings": warnings,
            "final_response": final_response,
            "final_report": final_response,
        }
    )
