from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


PACKAGE_ROOT = Path(__file__).resolve().parents[2]
WORKSPACE_ROOT = PACKAGE_ROOT.parent


def _load_env_file(path: Path) -> None:
    if not path.exists():
        return
    for raw_line in path.read_text(encoding="utf-8-sig").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


_load_env_file(WORKSPACE_ROOT / ".env")
_load_env_file(PACKAGE_ROOT / ".env")


def _get_int_env(name: str, default: int) -> int:
    value = os.getenv(name)
    if value is None or value == "":
        return default
    return int(value)


def _get_bool_env(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() not in ("0", "false", "no", "off", "")


def _get_float_env(name: str, default: float) -> float:
    value = os.getenv(name)
    if value is None or value == "":
        return default
    return float(value)


def _default_embedding_dim() -> int:
    provider = os.getenv("RAG_EMBEDDING_PROVIDER", "local").strip().lower()
    return 1024 if provider == "local" else 1536


@dataclass(frozen=True)
class RagConfig:
    package_root: Path = PACKAGE_ROOT
    workspace_root: Path = WORKSPACE_ROOT
    data_dir: Path = Path(os.getenv("RAG_DATA_DIR", str(PACKAGE_ROOT / "data")))
    raw_dir: Path = Path(os.getenv("RAG_RAW_DIR", str(PACKAGE_ROOT / "data" / "raw")))
    parsed_dir: Path = Path(os.getenv("RAG_PARSED_DIR", str(PACKAGE_ROOT / "data" / "parsed")))
    manifest_path: Path = Path(
        os.getenv("RAG_MANIFEST_PATH", str(PACKAGE_ROOT / "data" / "manifest.json"))
    )
    milvus_uri: str = os.getenv("MILVUS_URI", "http://127.0.0.1:19530")
    milvus_token: str | None = os.getenv("MILVUS_TOKEN") or None
    collection_name: str = os.getenv("RAG_COLLECTION", "invesagent_policy_docs")
    embedding_provider: str = os.getenv("RAG_EMBEDDING_PROVIDER", "local").strip().lower()
    embedding_model: str = os.getenv("RAG_EMBEDDING_MODEL", "BAAI/bge-m3")
    embedding_dim: int = _get_int_env("RAG_EMBEDDING_DIM", _default_embedding_dim())
    embedding_device: str | None = os.getenv("RAG_EMBEDDING_DEVICE") or None
    embedding_local_files_only: bool = _get_bool_env("RAG_EMBEDDING_LOCAL_FILES_ONLY", False)
    embedding_batch_size: int = _get_int_env("RAG_EMBEDDING_BATCH_SIZE", 4)
    chunk_size: int = _get_int_env("RAG_CHUNK_SIZE", 900)
    chunk_overlap: int = _get_int_env("RAG_CHUNK_OVERLAP", 120)
    ingest_batch_size: int = _get_int_env("RAG_INGEST_BATCH_SIZE", 64)
    top_k: int = _get_int_env("RAG_TOP_K", 8)
    hybrid_dense_weight: float = _get_float_env("RAG_HYBRID_DENSE_WEIGHT", 0.65)


def get_config() -> RagConfig:
    return RagConfig()
