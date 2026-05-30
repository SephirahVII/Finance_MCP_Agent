from __future__ import annotations

import argparse
import json
from dataclasses import asdict

from invesagent_rag.config import get_config
from invesagent_rag.ingest import RagIngestor
from invesagent_rag.milvus_store import MilvusStore
from invesagent_rag.prepare import prepare_all, prepare_company_report, prepare_macro_policy
from invesagent_rag.retriever import RagRetriever


def _cmd_init_store(args: argparse.Namespace) -> None:
    config = get_config()
    store = MilvusStore(
        uri=config.milvus_uri,
        token=config.milvus_token,
        collection_name=config.collection_name,
        dimension=config.embedding_dim,
    )
    store.ensure_collection(drop_existing=args.drop)
    print(
        json.dumps(
            {
                "collection": config.collection_name,
                "milvus_uri": config.milvus_uri,
                "dimension": config.embedding_dim,
                "dropped": args.drop,
            },
            ensure_ascii=False,
            indent=2,
        )
    )


def _cmd_ingest(args: argparse.Namespace) -> None:
    ingestor = RagIngestor()
    if args.source == "macro_policy":
        stats = ingestor.ingest_macro_policy(limit=args.limit, force=args.force)
    elif args.source == "company_report":
        stats = ingestor.ingest_company_report(limit=args.limit, force=args.force)
    else:
        stats = ingestor.ingest_all(limit=args.limit, force=args.force)
    print(json.dumps(asdict(stats), ensure_ascii=False, indent=2))


def _cmd_prepare(args: argparse.Namespace) -> None:
    if args.source == "macro_policy":
        payload = asdict(prepare_macro_policy(limit=args.limit))
    elif args.source == "company_report":
        payload = asdict(prepare_company_report(limit=args.limit))
    else:
        payload = {key: asdict(value) for key, value in prepare_all(limit=args.limit).items()}
    print(json.dumps(payload, ensure_ascii=False, indent=2))


def _cmd_query(args: argparse.Namespace) -> None:
    source_type = None if args.source == "all" else args.source
    hits = RagRetriever().retrieve(
        args.query,
        source_type=source_type,
        level=args.level,
        region=args.region,
        start_year=args.start_year,
        end_year=args.end_year,
        symbol=args.symbol,
        company_name=args.company_name,
        report_year=args.report_year,
        top_k=args.top_k,
        mode=args.mode,
    )
    payload = [
        {
            "rank": index + 1,
            "score": hit.score,
            "dense_score": hit.dense_score,
            "bm25_score": hit.bm25_score,
            "method": hit.retrieval_method,
            "title": hit.title,
            "region": hit.region,
            "year": hit.year,
            "level": hit.jurisdiction_level,
            "symbol": hit.symbol,
            "company_name": hit.company_name,
            "report_year": hit.report_year,
            "report_type": hit.report_type,
            "section_path": hit.section_path,
            "content_categories": hit.content_categories,
            "policy_tools": hit.policy_tools,
            "mentioned_industries": hit.mentioned_industries,
            "chunk_id": hit.chunk_id,
            "source_path": hit.source_path,
            "text": hit.text[: args.preview_chars],
        }
        for index, hit in enumerate(hits)
    ]
    print(json.dumps(payload, ensure_ascii=False, indent=2))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Build and query the InvesAgent RAG store.")
    sub = parser.add_subparsers(dest="command", required=True)

    init_store = sub.add_parser("init-store", help="Create the Milvus collection.")
    init_store.add_argument("--drop", action="store_true", help="Drop and recreate the collection.")
    init_store.set_defaults(func=_cmd_init_store)

    ingest = sub.add_parser("ingest", help="Ingest txt documents into Milvus.")
    ingest.add_argument(
        "--source",
        choices=["macro_policy", "company_report", "all"],
        default="macro_policy",
        help="Document source to ingest.",
    )
    ingest.add_argument("--limit", type=int, default=None, help="Only ingest the first N txt files.")
    ingest.add_argument("--force", action="store_true", help="Re-embed files even if unchanged.")
    ingest.set_defaults(func=_cmd_ingest)

    prepare = sub.add_parser(
        "prepare",
        help="Parse txt documents and write metadata/chunk plans without embeddings or Milvus.",
    )
    prepare.add_argument(
        "--source",
        choices=["macro_policy", "company_report", "all"],
        default="macro_policy",
        help="Document source to prepare.",
    )
    prepare.add_argument("--limit", type=int, default=None, help="Only prepare the first N txt files.")
    prepare.set_defaults(func=_cmd_prepare)

    query = sub.add_parser("query", help="Search RAG documents.")
    query.add_argument("query")
    query.add_argument("--source", choices=["macro_policy", "company_report", "all"], default="macro_policy")
    query.add_argument("--level", choices=["central", "province", "prefecture"], default=None)
    query.add_argument("--region", default=None)
    query.add_argument("--start-year", type=int, default=None)
    query.add_argument("--end-year", type=int, default=None)
    query.add_argument("--symbol", default=None)
    query.add_argument("--company-name", default=None)
    query.add_argument("--report-year", type=int, default=None)
    query.add_argument("--top-k", type=int, default=None)
    query.add_argument("--mode", choices=["hybrid", "dense", "bm25"], default="hybrid")
    query.add_argument("--preview-chars", type=int, default=300)
    query.set_defaults(func=_cmd_query)
    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
