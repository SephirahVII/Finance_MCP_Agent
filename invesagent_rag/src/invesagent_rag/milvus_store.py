from __future__ import annotations

from typing import Any

from invesagent_rag.schema import RagChunk, RetrievalHit


class MilvusStore:
    def __init__(self, uri: str, collection_name: str, dimension: int, token: str | None = None) -> None:
        try:
            from pymilvus import DataType, MilvusClient
            from pymilvus.exceptions import MilvusException
        except ModuleNotFoundError as exc:
            raise RuntimeError("Install pymilvus to use the RAG Milvus store.") from exc
        self.DataType = DataType
        try:
            self.client = MilvusClient(uri=uri, token=token)
        except MilvusException as exc:
            raise RuntimeError(
                "Unable to connect to Milvus at "
                f"{uri}. Start the Milvus server, update MILVUS_URI, or run query "
                "with --mode bm25 to use the local metadata index without Milvus."
            ) from None
        self.collection_name = collection_name
        self.dimension = dimension

    def ensure_collection(self, drop_existing: bool = False) -> None:
        if self.client.has_collection(self.collection_name):
            if not drop_existing:
                return
            self.client.drop_collection(self.collection_name)

        schema = self.client.create_schema(auto_id=False, enable_dynamic_field=True)
        schema.add_field("id", self.DataType.VARCHAR, is_primary=True, max_length=64)
        schema.add_field("embedding", self.DataType.FLOAT_VECTOR, dim=self.dimension)
        schema.add_field("doc_id", self.DataType.VARCHAR, max_length=64)
        schema.add_field("chunk_id", self.DataType.VARCHAR, max_length=64)
        schema.add_field("text", self.DataType.VARCHAR, max_length=8192)
        schema.add_field("title", self.DataType.VARCHAR, max_length=512)
        schema.add_field("source_type", self.DataType.VARCHAR, max_length=64)
        schema.add_field("source_name", self.DataType.VARCHAR, max_length=128)
        schema.add_field("source_path", self.DataType.VARCHAR, max_length=1024)
        schema.add_field("jurisdiction_level", self.DataType.VARCHAR, max_length=32)
        schema.add_field("region", self.DataType.VARCHAR, max_length=128)
        schema.add_field("year", self.DataType.INT64)
        schema.add_field("published_at", self.DataType.INT64)
        schema.add_field("market", self.DataType.VARCHAR, max_length=16)
        schema.add_field("url", self.DataType.VARCHAR, max_length=1024)
        schema.add_field("topics", self.DataType.VARCHAR, max_length=1024)
        schema.add_field("symbol", self.DataType.VARCHAR, max_length=32)
        schema.add_field("company_name", self.DataType.VARCHAR, max_length=128)
        schema.add_field("report_year", self.DataType.INT64)
        schema.add_field("report_type", self.DataType.VARCHAR, max_length=64)
        schema.add_field("section_level_1", self.DataType.VARCHAR, max_length=512)
        schema.add_field("section_level_2", self.DataType.VARCHAR, max_length=512)
        schema.add_field("section_level_3", self.DataType.VARCHAR, max_length=512)
        schema.add_field("section_path", self.DataType.VARCHAR, max_length=1024)
        schema.add_field("content_categories", self.DataType.VARCHAR, max_length=512)
        schema.add_field("policy_tools", self.DataType.VARCHAR, max_length=512)
        schema.add_field("mentioned_industries", self.DataType.VARCHAR, max_length=512)

        index_params = self.client.prepare_index_params()
        index_params.add_index(
            field_name="embedding",
            index_type="AUTOINDEX",
            metric_type="COSINE",
        )
        self.client.create_collection(
            collection_name=self.collection_name,
            schema=schema,
            index_params=index_params,
        )

    def upsert_chunks(self, chunks: list[RagChunk], embeddings: list[list[float]]) -> int:
        if len(chunks) != len(embeddings):
            raise ValueError("chunks and embeddings must have the same length.")
        rows = []
        for chunk, embedding in zip(chunks, embeddings):
            rows.append(
                {
                    "id": chunk.chunk_id,
                    "embedding": embedding,
                    "doc_id": chunk.doc_id,
                    "chunk_id": chunk.chunk_id,
                    "text": chunk.text[:8192],
                    "title": chunk.title[:512],
                    "source_type": chunk.source_type,
                    "source_name": chunk.source_name,
                    "source_path": chunk.source_path[:1024],
                    "jurisdiction_level": chunk.jurisdiction_level,
                    "region": chunk.region,
                    "year": int(chunk.year or 0),
                    "published_at": int(chunk.published_at or 0),
                    "market": chunk.market,
                    "url": chunk.url[:1024],
                    "topics": ",".join(chunk.topics)[:1024],
                    "symbol": chunk.symbol[:32],
                    "company_name": chunk.company_name[:128],
                    "report_year": int(chunk.report_year or 0),
                    "report_type": chunk.report_type[:64],
                    "section_level_1": chunk.section_level_1[:512],
                    "section_level_2": chunk.section_level_2[:512],
                    "section_level_3": chunk.section_level_3[:512],
                    "section_path": chunk.section_path[:1024],
                    "content_categories": ",".join(chunk.content_categories)[:512],
                    "policy_tools": ",".join(chunk.policy_tools)[:512],
                    "mentioned_industries": ",".join(chunk.mentioned_industries)[:512],
                }
            )
        if not rows:
            return 0
        if hasattr(self.client, "upsert"):
            result = self.client.upsert(collection_name=self.collection_name, data=rows)
        else:
            result = self.client.insert(collection_name=self.collection_name, data=rows)
        return int(result.get("upsert_count") or result.get("insert_count") or len(rows))

    def search(
        self,
        query_embedding: list[float],
        *,
        top_k: int = 8,
        filter_expr: str | None = None,
    ) -> list[RetrievalHit]:
        output_fields = [
            "doc_id",
            "chunk_id",
            "text",
            "title",
            "source_type",
            "source_name",
            "source_path",
            "jurisdiction_level",
            "region",
            "year",
            "topics",
            "symbol",
            "company_name",
            "report_year",
            "report_type",
            "section_path",
            "content_categories",
            "policy_tools",
            "mentioned_industries",
        ]
        results = self.client.search(
            collection_name=self.collection_name,
            data=[query_embedding],
            limit=top_k,
            filter=filter_expr,
            output_fields=output_fields,
        )
        hits: list[RetrievalHit] = []
        for item in results[0] if results else []:
            entity: dict[str, Any] = item.get("entity", {})
            topics = [value for value in str(entity.get("topics", "")).split(",") if value]
            content_categories = [
                value for value in str(entity.get("content_categories", "")).split(",") if value
            ]
            policy_tools = [value for value in str(entity.get("policy_tools", "")).split(",") if value]
            mentioned_industries = [
                value for value in str(entity.get("mentioned_industries", "")).split(",") if value
            ]
            hits.append(
                RetrievalHit(
                    chunk_id=str(entity.get("chunk_id", "")),
                    doc_id=str(entity.get("doc_id", "")),
                    text=str(entity.get("text", "")),
                    score=float(item.get("distance", 0.0)),
                    title=str(entity.get("title", "")),
                    source_type=str(entity.get("source_type", "")),
                    source_name=str(entity.get("source_name", "")),
                    jurisdiction_level=str(entity.get("jurisdiction_level", "")),
                    region=str(entity.get("region", "")),
                    year=int(entity.get("year") or 0) or None,
                    source_path=str(entity.get("source_path", "")),
                    topics=topics,
                    symbol=str(entity.get("symbol", "")),
                    company_name=str(entity.get("company_name", "")),
                    report_year=int(entity.get("report_year") or 0) or None,
                    report_type=str(entity.get("report_type", "")),
                    section_path=str(entity.get("section_path", "")),
                    content_categories=content_categories,
                    policy_tools=policy_tools,
                    mentioned_industries=mentioned_industries,
                    dense_score=float(item.get("distance", 0.0)),
                )
            )
        return hits
