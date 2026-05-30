from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Callable

from invesagent_rag.chunker import chunk_document
from invesagent_rag.cleaner import clean_text
from invesagent_rag.config import RagConfig, get_config
from invesagent_rag.embeddings import build_embedder
from invesagent_rag.manifest import Manifest
from invesagent_rag.milvus_store import MilvusStore
from invesagent_rag.schema import RagDocument, SourceFile
from invesagent_rag.text_loader import (
    iter_txt_files,
    load_company_report_document,
    load_policy_document,
)

DocumentLoader = Callable[[Path, Path], tuple[RagDocument, SourceFile]]


@dataclass(frozen=True)
class IngestStats:
    files_seen: int = 0
    files_ingested: int = 0
    files_skipped: int = 0
    chunks_ingested: int = 0
    source_type: str = "all"

    def add(self, other: "IngestStats") -> "IngestStats":
        return IngestStats(
            files_seen=self.files_seen + other.files_seen,
            files_ingested=self.files_ingested + other.files_ingested,
            files_skipped=self.files_skipped + other.files_skipped,
            chunks_ingested=self.chunks_ingested + other.chunks_ingested,
            source_type="all",
        )


class RagIngestor:
    def __init__(self, config: RagConfig | None = None) -> None:
        self.config = config or get_config()
        self.embedder = build_embedder(self.config)
        self.store = MilvusStore(
            uri=self.config.milvus_uri,
            token=self.config.milvus_token,
            collection_name=self.config.collection_name,
            dimension=self.config.embedding_dim,
        )

    def ingest_source(
        self,
        *,
        source_type: str,
        raw_subdir: str,
        loader: DocumentLoader,
        limit: int | None = None,
        force: bool = False,
    ) -> IngestStats:
        raw_root = self.config.raw_dir / raw_subdir
        files = iter_txt_files(raw_root)
        if limit is not None:
            files = files[:limit]

        self.store.ensure_collection()
        manifest = Manifest.load(self.config.manifest_path)

        files_ingested = 0
        files_skipped = 0
        chunks_ingested = 0

        for path in files:
            document, src = loader(path, self.config.raw_dir)
            if not force and manifest.is_current(src.relative_path, src.md5):
                files_skipped += 1
                continue

            document = type(document)(
                **{
                    **document.__dict__,
                    "text": clean_text(document.text),
                }
            )
            chunks = chunk_document(
                document,
                chunk_size=self.config.chunk_size,
                overlap=self.config.chunk_overlap,
            )
            for start in range(0, len(chunks), self.config.ingest_batch_size):
                batch = chunks[start : start + self.config.ingest_batch_size]
                embeddings = self.embedder.embed_texts([chunk.text for chunk in batch])
                chunks_ingested += self.store.upsert_chunks(batch, embeddings)

            manifest.mark_ingested(src.relative_path, src.md5, len(chunks))
            manifest.save()
            files_ingested += 1

        return IngestStats(
            files_seen=len(files),
            files_ingested=files_ingested,
            files_skipped=files_skipped,
            chunks_ingested=chunks_ingested,
            source_type=source_type,
        )

    def ingest_macro_policy(self, *, limit: int | None = None, force: bool = False) -> IngestStats:
        return self.ingest_source(
            source_type="macro_policy",
            raw_subdir="macro_policy",
            loader=load_policy_document,
            limit=limit,
            force=force,
        )

    def ingest_company_report(self, *, limit: int | None = None, force: bool = False) -> IngestStats:
        return self.ingest_source(
            source_type="company_report",
            raw_subdir="company_report",
            loader=load_company_report_document,
            limit=limit,
            force=force,
        )

    def ingest_all(self, *, limit: int | None = None, force: bool = False) -> IngestStats:
        stats = IngestStats()
        stats = stats.add(self.ingest_macro_policy(limit=limit, force=force))
        stats = stats.add(self.ingest_company_report(limit=limit, force=force))
        return stats


def build_macro_policy_rag(limit: int | None = None, force: bool = False) -> IngestStats:
    return RagIngestor().ingest_macro_policy(limit=limit, force=force)


def build_company_report_rag(limit: int | None = None, force: bool = False) -> IngestStats:
    return RagIngestor().ingest_company_report(limit=limit, force=force)
