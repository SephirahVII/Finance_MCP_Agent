from __future__ import annotations

import json
import math
import re
from collections import Counter
from dataclasses import dataclass
from pathlib import Path

from invesagent_rag.schema import RetrievalHit


TOKEN_RE = re.compile(r"[A-Za-z0-9]+|[\u4e00-\u9fff]")


def tokenize(text: str) -> list[str]:
    raw = TOKEN_RE.findall(text.lower())
    tokens: list[str] = []
    chinese_buffer = ""
    for item in raw:
        if len(item) == 1 and "\u4e00" <= item <= "\u9fff":
            chinese_buffer += item
            continue
        if chinese_buffer:
            tokens.extend(_chinese_tokens(chinese_buffer))
            chinese_buffer = ""
        tokens.append(item)
    if chinese_buffer:
        tokens.extend(_chinese_tokens(chinese_buffer))
    return tokens


def _chinese_tokens(text: str) -> list[str]:
    if len(text) <= 2:
        return [text]
    tokens = list(text)
    tokens.extend(text[index : index + 2] for index in range(len(text) - 1))
    return tokens


@dataclass
class Bm25Record:
    chunk_id: str
    doc_id: str
    text: str
    title: str
    source_type: str
    source_name: str
    source_path: str
    jurisdiction_level: str
    region: str
    year: int | None
    topics: list[str]
    symbol: str
    company_name: str
    report_year: int | None
    report_type: str
    section_path: str
    content_categories: list[str]
    policy_tools: list[str]
    mentioned_industries: list[str]
    tokens: list[str]


def _as_list(value) -> list[str]:
    if isinstance(value, list):
        return [str(item) for item in value if item]
    return [item for item in str(value or "").split(",") if item]


class Bm25Index:
    def __init__(self, records: list[Bm25Record]) -> None:
        self.records = records
        self.doc_freq: Counter[str] = Counter()
        self.term_freqs: list[Counter[str]] = []
        self.doc_lengths: list[int] = []
        for record in records:
            tf = Counter(record.tokens)
            self.term_freqs.append(tf)
            self.doc_lengths.append(len(record.tokens))
            self.doc_freq.update(tf.keys())
        self.avg_doc_len = sum(self.doc_lengths) / max(len(self.doc_lengths), 1)

    @classmethod
    def from_jsonl(cls, path: Path | list[Path]) -> "Bm25Index":
        records: list[Bm25Record] = []
        paths = path if isinstance(path, list) else [path]
        for jsonl_path in paths:
            if not jsonl_path.exists():
                continue
            with jsonl_path.open("r", encoding="utf-8") as handle:
                for line in handle:
                    if not line.strip():
                        continue
                    row = json.loads(line)
                    text = row.get("text") or row.get("text_preview") or ""
                    records.append(
                        Bm25Record(
                            chunk_id=str(row.get("chunk_id", "")),
                            doc_id=str(row.get("doc_id", "")),
                            text=text,
                            title=str(row.get("title", "")),
                            source_type=str(row.get("source_type", "")),
                            source_name=str(row.get("source_name", "")),
                            source_path=str(row.get("source_path", "")),
                            jurisdiction_level=str(row.get("jurisdiction_level", "")),
                            region=str(row.get("region", "")),
                            year=int(row.get("year") or 0) or None,
                            topics=_as_list(row.get("topics")),
                            symbol=str(row.get("symbol", "")),
                            company_name=str(row.get("company_name", "")),
                            report_year=int(row.get("report_year") or 0) or None,
                            report_type=str(row.get("report_type", "")),
                            section_path=str(row.get("section_path", "")),
                            content_categories=_as_list(row.get("content_categories")),
                            policy_tools=_as_list(row.get("policy_tools")),
                            mentioned_industries=_as_list(row.get("mentioned_industries")),
                            tokens=tokenize(
                                " ".join(
                                    [
                                        str(row.get("title", "")),
                                        str(row.get("symbol", "")),
                                        str(row.get("company_name", "")),
                                        str(row.get("report_type", "")),
                                        str(row.get("section_path", "")),
                                        ",".join(_as_list(row.get("content_categories"))),
                                        ",".join(_as_list(row.get("policy_tools"))),
                                        ",".join(_as_list(row.get("mentioned_industries"))),
                                        text,
                                    ]
                                )
                            ),
                        )
                    )
        return cls(records)

    def search(
        self,
        query: str,
        *,
        top_k: int = 20,
        level: str | None = None,
        region: str | None = None,
        start_year: int | None = None,
        end_year: int | None = None,
        source_type: str | None = None,
        symbol: str | None = None,
        company_name: str | None = None,
        report_year: int | None = None,
    ) -> list[RetrievalHit]:
        query_terms = tokenize(query)
        if not query_terms or not self.records:
            return []
        scores: list[tuple[float, int]] = []
        for index, record in enumerate(self.records):
            if source_type and record.source_type != source_type:
                continue
            if level and record.jurisdiction_level != level:
                continue
            if region and record.region != region:
                continue
            if symbol and record.symbol != symbol:
                continue
            if company_name and company_name not in record.company_name:
                continue
            if report_year is not None and record.report_year != report_year:
                continue
            if start_year is not None and (record.year is None or record.year < start_year):
                continue
            if end_year is not None and (record.year is None or record.year > end_year):
                continue
            score = self._score(query_terms, index)
            if score > 0:
                scores.append((score, index))
        scores.sort(reverse=True, key=lambda item: item[0])
        return [self._hit(self.records[index], score) for score, index in scores[:top_k]]

    def _score(self, query_terms: list[str], doc_index: int, k1: float = 1.5, b: float = 0.75) -> float:
        score = 0.0
        tf = self.term_freqs[doc_index]
        doc_len = self.doc_lengths[doc_index]
        corpus_size = len(self.records)
        for term in query_terms:
            freq = tf.get(term, 0)
            if freq == 0:
                continue
            df = self.doc_freq.get(term, 0)
            idf = math.log(1 + (corpus_size - df + 0.5) / (df + 0.5))
            denom = freq + k1 * (1 - b + b * doc_len / max(self.avg_doc_len, 1))
            score += idf * (freq * (k1 + 1) / denom)
        return score

    def _hit(self, record: Bm25Record, score: float) -> RetrievalHit:
        return RetrievalHit(
            chunk_id=record.chunk_id,
            doc_id=record.doc_id,
            text=record.text,
            score=score,
            title=record.title,
            source_type=record.source_type,
            source_name=record.source_name,
            jurisdiction_level=record.jurisdiction_level,
            region=record.region,
            year=record.year,
            source_path=record.source_path,
            topics=record.topics,
            symbol=record.symbol,
            company_name=record.company_name,
            report_year=record.report_year,
            report_type=record.report_type,
            section_path=record.section_path,
            content_categories=record.content_categories,
            policy_tools=record.policy_tools,
            mentioned_industries=record.mentioned_industries,
            bm25_score=score,
            retrieval_method="bm25",
        )
