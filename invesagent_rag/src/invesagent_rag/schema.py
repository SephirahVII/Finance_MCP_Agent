from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class RagDocument:
    doc_id: str
    title: str
    text: str
    source_type: str
    source_name: str
    source_path: str
    jurisdiction_level: str
    region: str
    year: int | None
    published_at: int | None = None
    market: str = "cn"
    url: str = ""
    topics: list[str] = field(default_factory=list)
    symbol: str = ""
    company_name: str = ""
    report_year: int | None = None
    report_type: str = ""


@dataclass(frozen=True)
class RagChunk:
    chunk_id: str
    doc_id: str
    chunk_index: int
    text: str
    title: str
    source_type: str
    source_name: str
    source_path: str
    jurisdiction_level: str
    region: str
    year: int | None
    published_at: int | None
    market: str
    url: str
    topics: list[str]
    symbol: str = ""
    company_name: str = ""
    report_year: int | None = None
    report_type: str = ""
    section_level_1: str = ""
    section_level_2: str = ""
    section_level_3: str = ""
    section_path: str = ""
    content_categories: list[str] = field(default_factory=list)
    policy_tools: list[str] = field(default_factory=list)
    mentioned_industries: list[str] = field(default_factory=list)

    def metadata(self) -> dict[str, Any]:
        return {
            "doc_id": self.doc_id,
            "chunk_id": self.chunk_id,
            "chunk_index": self.chunk_index,
            "title": self.title,
            "source_type": self.source_type,
            "source_name": self.source_name,
            "source_path": self.source_path,
            "jurisdiction_level": self.jurisdiction_level,
            "region": self.region,
            "year": self.year,
            "published_at": self.published_at,
            "market": self.market,
            "url": self.url,
            "topics": self.topics,
            "symbol": self.symbol,
            "company_name": self.company_name,
            "report_year": self.report_year,
            "report_type": self.report_type,
            "section_level_1": self.section_level_1,
            "section_level_2": self.section_level_2,
            "section_level_3": self.section_level_3,
            "section_path": self.section_path,
            "content_categories": self.content_categories,
            "policy_tools": self.policy_tools,
            "mentioned_industries": self.mentioned_industries,
        }


@dataclass(frozen=True)
class RetrievalHit:
    chunk_id: str
    doc_id: str
    text: str
    score: float
    title: str
    source_type: str
    source_name: str
    jurisdiction_level: str
    region: str
    year: int | None
    source_path: str
    topics: list[str]
    symbol: str = ""
    company_name: str = ""
    report_year: int | None = None
    report_type: str = ""
    section_path: str = ""
    content_categories: list[str] = field(default_factory=list)
    policy_tools: list[str] = field(default_factory=list)
    mentioned_industries: list[str] = field(default_factory=list)
    dense_score: float | None = None
    bm25_score: float | None = None
    retrieval_method: str = "dense"


@dataclass(frozen=True)
class SourceFile:
    path: Path
    relative_path: str
    md5: str
