from __future__ import annotations

from dataclasses import dataclass

from invesagent_rag.bm25 import Bm25Index
from invesagent_rag.config import RagConfig, get_config
from invesagent_rag.embeddings import build_embedder
from invesagent_rag.milvus_store import MilvusStore
from invesagent_rag.schema import RetrievalHit


def _quote(value: str) -> str:
    return value.replace("\\", "\\\\").replace('"', '\\"')


@dataclass
class RagRetriever:
    config: RagConfig | None = None

    def __post_init__(self) -> None:
        self.config = self.config or get_config()
        self._embedder = None
        self._store = None
        self._bm25_indexes: dict[str, Bm25Index] = {}

    @property
    def embedder(self):
        if self._embedder is None:
            self._embedder = build_embedder(self.config)
        return self._embedder

    @property
    def store(self) -> MilvusStore:
        if self._store is None:
            self._store = MilvusStore(
                uri=self.config.milvus_uri,
                token=self.config.milvus_token,
                collection_name=self.config.collection_name,
                dimension=self.config.embedding_dim,
            )
        return self._store

    def bm25(self, source_type: str | None = None) -> Bm25Index:
        key = source_type or "all"
        if key not in self._bm25_indexes:
            metadata_dir = self.config.data_dir / "metadata"
            if source_type:
                paths = [metadata_dir / f"{source_type}_chunks.jsonl"]
            else:
                paths = [
                    metadata_dir / "macro_policy_chunks.jsonl",
                    metadata_dir / "company_report_chunks.jsonl",
                ]
            self._bm25_indexes[key] = Bm25Index.from_jsonl(paths)
        return self._bm25_indexes[key]

    def retrieve(
        self,
        query: str,
        *,
        source_type: str | None = None,
        level: str | None = None,
        region: str | None = None,
        start_year: int | None = None,
        end_year: int | None = None,
        symbol: str | None = None,
        company_name: str | None = None,
        report_year: int | None = None,
        top_k: int | None = None,
        mode: str = "hybrid",
    ) -> list[RetrievalHit]:
        top_k = top_k or self.config.top_k
        if mode == "bm25":
            return self.bm25(source_type).search(
                query,
                top_k=top_k,
                level=level,
                region=region,
                start_year=start_year,
                end_year=end_year,
                source_type=source_type,
                symbol=symbol,
                company_name=company_name,
                report_year=report_year,
            )

        filters = []
        if source_type:
            filters.append(f'source_type == "{_quote(source_type)}"')
        if level:
            filters.append(f'jurisdiction_level == "{_quote(level)}"')
        if region:
            filters.append(f'region == "{_quote(region)}"')
        if symbol:
            filters.append(f'symbol == "{_quote(symbol)}"')
        if company_name:
            filters.append(f'company_name == "{_quote(company_name)}"')
        if report_year is not None:
            filters.append(f"report_year == {int(report_year)}")
        if start_year is not None:
            filters.append(f"year >= {int(start_year)}")
        if end_year is not None:
            filters.append(f"year <= {int(end_year)}")
        filter_expr = " and ".join(filters) if filters else None
        query_embedding = self.embedder.embed_query(query)
        dense_hits = self.store.search(
            query_embedding,
            top_k=top_k if mode == "dense" else top_k * 4,
            filter_expr=filter_expr,
        )
        if mode == "dense":
            return dense_hits
        bm25_hits = self.bm25(source_type).search(
            query,
            top_k=top_k * 4,
            level=level,
            region=region,
            start_year=start_year,
            end_year=end_year,
            source_type=source_type,
            symbol=symbol,
            company_name=company_name,
            report_year=report_year,
        )
        return _combine_hybrid(
            dense_hits,
            bm25_hits,
            top_k=top_k,
            dense_weight=self.config.hybrid_dense_weight,
        )

    def retrieve_policy(
        self,
        query: str,
        *,
        level: str | None = None,
        region: str | None = None,
        start_year: int | None = None,
        end_year: int | None = None,
        top_k: int | None = None,
        mode: str = "hybrid",
    ) -> list[RetrievalHit]:
        return self.retrieve(
            query,
            source_type="macro_policy",
            level=level,
            region=region,
            start_year=start_year,
            end_year=end_year,
            top_k=top_k,
            mode=mode,
        )

    def retrieve_company_report(
        self,
        query: str,
        *,
        symbol: str | None = None,
        company_name: str | None = None,
        report_year: int | None = None,
        top_k: int | None = None,
        mode: str = "hybrid",
    ) -> list[RetrievalHit]:
        return self.retrieve(
            query,
            source_type="company_report",
            symbol=symbol,
            company_name=company_name,
            report_year=report_year,
            top_k=top_k,
            mode=mode,
        )


def _normalize(values: dict[str, float]) -> dict[str, float]:
    if not values:
        return {}
    low = min(values.values())
    high = max(values.values())
    if high <= low:
        return {key: 1.0 for key in values}
    return {key: (value - low) / (high - low) for key, value in values.items()}


def _combine_hybrid(
    dense_hits: list[RetrievalHit],
    bm25_hits: list[RetrievalHit],
    *,
    top_k: int,
    dense_weight: float,
) -> list[RetrievalHit]:
    by_id: dict[str, RetrievalHit] = {}
    dense_scores = {hit.chunk_id: float(hit.dense_score if hit.dense_score is not None else hit.score) for hit in dense_hits}
    bm25_scores = {hit.chunk_id: float(hit.bm25_score if hit.bm25_score is not None else hit.score) for hit in bm25_hits}
    dense_norm = _normalize(dense_scores)
    bm25_norm = _normalize(bm25_scores)
    for hit in [*bm25_hits, *dense_hits]:
        by_id.setdefault(hit.chunk_id, hit)

    combined: list[RetrievalHit] = []
    sparse_weight = 1 - dense_weight
    for chunk_id, hit in by_id.items():
        dense_score = dense_scores.get(chunk_id)
        bm25_score = bm25_scores.get(chunk_id)
        score = dense_weight * dense_norm.get(chunk_id, 0.0) + sparse_weight * bm25_norm.get(chunk_id, 0.0)
        combined.append(
            RetrievalHit(
                **{
                    **hit.__dict__,
                    "score": score,
                    "dense_score": dense_score,
                    "bm25_score": bm25_score,
                    "retrieval_method": "hybrid",
                }
            )
        )
    combined.sort(key=lambda hit: hit.score, reverse=True)
    return combined[:top_k]
