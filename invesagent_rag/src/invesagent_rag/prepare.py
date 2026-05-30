from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Callable

from invesagent_rag.chunker import chunk_document
from invesagent_rag.cleaner import clean_text
from invesagent_rag.config import RagConfig, get_config
from invesagent_rag.schema import RagDocument, SourceFile
from invesagent_rag.text_loader import (
    iter_txt_files,
    load_company_report_document,
    load_policy_document,
)

DocumentLoader = Callable[[Path, Path], tuple[RagDocument, SourceFile]]


@dataclass(frozen=True)
class PrepareStats:
    files_seen: int
    metadata_written: int
    parsed_written: int
    chunks_planned: int
    output_dir: str
    source_type: str = "all"


def _write_jsonl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")


def _prepare_source(
    *,
    source_type: str,
    raw_subdir: str,
    loader: DocumentLoader,
    limit: int | None,
    config: RagConfig,
) -> PrepareStats:
    raw_root = config.raw_dir / raw_subdir
    parsed_root = config.parsed_dir / raw_subdir
    metadata_path = config.data_dir / "metadata" / f"{source_type}_documents.jsonl"
    chunk_plan_path = config.data_dir / "metadata" / f"{source_type}_chunks.jsonl"

    files = iter_txt_files(raw_root)
    if limit is not None:
        files = files[:limit]

    metadata_rows: list[dict] = []
    chunk_rows: list[dict] = []
    parsed_written = 0

    for path in files:
        document, source = loader(path, config.raw_dir)
        cleaned_text = clean_text(document.text)
        parsed_path = parsed_root / Path(source.relative_path).relative_to(raw_subdir)
        parsed_path.parent.mkdir(parents=True, exist_ok=True)
        parsed_path.write_text(cleaned_text, encoding="utf-8")
        parsed_written += 1

        clean_document = type(document)(**{**document.__dict__, "text": cleaned_text})
        chunks = chunk_document(
            clean_document,
            chunk_size=config.chunk_size,
            overlap=config.chunk_overlap,
        )

        metadata_rows.append(
            {
                "doc_id": document.doc_id,
                "title": document.title,
                "source_type": document.source_type,
                "source_name": document.source_name,
                "source_path": document.source_path,
                "parsed_path": parsed_path.relative_to(config.data_dir).as_posix(),
                "jurisdiction_level": document.jurisdiction_level,
                "region": document.region,
                "year": document.year,
                "published_at": document.published_at,
                "market": document.market,
                "url": document.url,
                "topics": document.topics,
                "symbol": document.symbol,
                "company_name": document.company_name,
                "report_year": document.report_year,
                "report_type": document.report_type,
                "md5": source.md5,
                "text_chars": len(cleaned_text),
                "chunk_count": len(chunks),
            }
        )

        for chunk in chunks:
            chunk_rows.append(
                {
                    **chunk.metadata(),
                    "text_chars": len(chunk.text),
                    "text_preview": chunk.text[:120],
                    "text": chunk.text,
                }
            )

    _write_jsonl(metadata_path, metadata_rows)
    _write_jsonl(chunk_plan_path, chunk_rows)
    return PrepareStats(
        files_seen=len(files),
        metadata_written=len(metadata_rows),
        parsed_written=parsed_written,
        chunks_planned=len(chunk_rows),
        output_dir=str((config.data_dir / "metadata").resolve()),
        source_type=source_type,
    )


def prepare_macro_policy(limit: int | None = None, config: RagConfig | None = None) -> PrepareStats:
    config = config or get_config()
    return _prepare_source(
        source_type="macro_policy",
        raw_subdir="macro_policy",
        loader=load_policy_document,
        limit=limit,
        config=config,
    )


def prepare_company_report(limit: int | None = None, config: RagConfig | None = None) -> PrepareStats:
    config = config or get_config()
    return _prepare_source(
        source_type="company_report",
        raw_subdir="company_report",
        loader=load_company_report_document,
        limit=limit,
        config=config,
    )


def prepare_all(limit: int | None = None, config: RagConfig | None = None) -> dict[str, PrepareStats]:
    config = config or get_config()
    stats = {
        "macro_policy": prepare_macro_policy(limit=limit, config=config),
        "company_report": prepare_company_report(limit=limit, config=config),
    }
    summary_path = config.data_dir / "metadata" / "prepare_summary.json"
    summary_path.parent.mkdir(parents=True, exist_ok=True)
    summary_path.write_text(
        json.dumps({key: asdict(value) for key, value in stats.items()}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return stats
