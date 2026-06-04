from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class FakeRetrievalHit:
    chunk_id: str = "policy-2024-001"
    doc_id: str = "policy-doc-2024"
    title: str = "Fiscal Policy and Domestic Demand"
    source_type: str = "macro_policy"
    source_name: str = "Government Work Report"
    jurisdiction_level: str = "central"
    region: str = "cn"
    year: int = 2024
    source_path: str = "data/raw/macro_policy/2024-policy.txt"
    text: str = "Fiscal policy supports domestic demand through targeted spending."
    score: float = 0.92
    dense_score: float | None = None
    bm25_score: float | None = 1.4
    retrieval_method: str = "bm25"
    topics: tuple[str, ...] = ("fiscal_policy", "domestic_demand")
    content_categories: tuple[str, ...] = ("policy",)
    policy_tools: tuple[str, ...] = ("fiscal_spending",)
    mentioned_industries: tuple[str, ...] = ()


def fake_retrieve_policy_evidence(
    query: str,
    *,
    start_year: int | None,
    end_year: int | None,
    top_k: int = 6,
) -> tuple[list[dict[str, Any]], list[str], str]:
    del query, start_year, end_year
    from invesagent_agent.agents.macro_policy_analyst import _hit_to_dict

    hits = [_hit_to_dict(FakeRetrievalHit()) for _ in range(max(min(top_k, 1), 1))]
    return hits, [], "bm25"

