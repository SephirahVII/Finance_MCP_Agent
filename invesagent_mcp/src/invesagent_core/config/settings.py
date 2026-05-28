from __future__ import annotations

import os
import sys
from dataclasses import dataclass
from pathlib import Path


def _get_int_env(name: str, default: int) -> int:
    value = os.getenv(name)
    if value is None or value == "":
        return default
    return int(value)


def _load_env_file(path: Path) -> None:
    """Load simple KEY=VALUE pairs from .env without requiring python-dotenv."""
    if not path.exists():
        return

    for raw_line in path.read_text(encoding="utf-8-sig").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue

        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip().lstrip("\ufeff"), value.strip().strip('"').strip("'"))


@dataclass(frozen=True)
class Settings:
    """Project settings loaded from environment variables and .env."""

    project_root: Path
    tushare_token: str | None
    openai_api_key: str | None
    deepseek_api_key: str | None
    openai_base_url: str | None
    deepseek_base_url: str | None
    openai_model: str | None
    deepseek_model: str | None
    llm_provider: str
    llm_base_url: str | None
    llm_model: str | None
    llm_record_usage: bool
    llm_prompt_cache: str
    mcp_python_path: str
    mcp_transport: str
    mcp_host: str
    mcp_port: int
    mcp_streamable_http_path: str
    model_name: str | None
    data_cache_dir: str
    charts_dir: str
    reports_dir: str
    default_index_code: str
    report_writing_mode: str


PROJECT_ROOT = Path(__file__).resolve().parents[4]
_load_env_file(PROJECT_ROOT / ".env")

settings = Settings(
    project_root=PROJECT_ROOT,
    tushare_token=os.getenv("TUSHARE_TOKEN") or None,
    openai_api_key=os.getenv("OPENAI_API_KEY") or None,
    deepseek_api_key=os.getenv("DEEPSEEK_API_KEY") or None,
    openai_base_url=os.getenv("OPENAI_BASE_URL") or None,
    deepseek_base_url=os.getenv("DEEPSEEK_BASE_URL") or None,
    openai_model=os.getenv("OPENAI_MODEL") or None,
    deepseek_model=os.getenv("DEEPSEEK_MODEL") or None,
    llm_provider=os.getenv("LLM_PROVIDER", "openai"),
    llm_base_url=os.getenv("LLM_BASE_URL") or None,
    llm_model=os.getenv("LLM_MODEL") or os.getenv("MODEL_NAME") or None,
    llm_record_usage=(
        os.getenv("LLM_RECORD_USAGE", "true").strip().lower()
        not in ("0", "false", "no", "off", "")
    ),
    llm_prompt_cache=os.getenv("LLM_PROMPT_CACHE", "auto"),
    mcp_python_path=os.getenv("MCP_PYTHON_PATH") or sys.executable,
    mcp_transport=os.getenv("MCP_TRANSPORT", "stdio"),
    mcp_host=os.getenv("MCP_HOST", "127.0.0.1"),
    mcp_port=_get_int_env("MCP_PORT", 8000),
    mcp_streamable_http_path=os.getenv("MCP_STREAMABLE_HTTP_PATH", "/mcp"),
    model_name=os.getenv("MODEL_NAME") or None,
    data_cache_dir=os.getenv("DATA_CACHE_DIR", ".runtime/data_cache"),
    charts_dir=os.getenv("CHARTS_DIR", ".runtime/charts"),
    reports_dir=os.getenv("REPORTS_DIR", ".runtime/reports"),
    default_index_code=os.getenv("DEFAULT_INDEX_CODE", "000300.SH"),
    report_writing_mode=os.getenv("REPORT_WRITING_MODE", "template"),
)
