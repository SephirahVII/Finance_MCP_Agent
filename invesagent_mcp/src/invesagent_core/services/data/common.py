from __future__ import annotations

import hashlib
import re
from dataclasses import replace
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, TypeVar

from invesagent_core.storage.cache import load_json_cache_with_ttl, save_json_cache
from invesagent_core.storage.paths import get_data_cache_dir


T = TypeVar("T")

DAY_SECONDS = 24 * 60 * 60


def classify_provider_error(error: Exception, provider: str, api_name: str) -> tuple[str, str]:
    """Normalize common provider errors into stable error_type values."""
    raw_error = str(error)
    lowered = raw_error.lower()

    if "not installed" in lowered or "no module named" in lowered:
        return "dependency_missing", raw_error
    if "timeout" in lowered or "timed out" in lowered:
        return "network_timeout", f"{provider} {api_name} request timed out."
    if "没有接口" in raw_error or "权限" in raw_error or "permission" in lowered:
        return "permission_denied", f"Current {provider} credential does not have {api_name} access."
    if "频率" in raw_error or "超限" in raw_error or "rate" in lowered or "limit" in lowered:
        return "rate_limited", f"{provider} {api_name} request is rate limited."
    if "schema" in lowered or "column" in lowered or "columns" in lowered:
        return "schema_changed", f"{provider} {api_name} response schema may have changed."

    return "provider_error", f"Failed to fetch {provider} {api_name} data."


def cache_path(namespace: str, **parts: Any) -> Path:
    """Build a deterministic cache path for a data request."""
    normalized = {
        key: str(value).strip().lower()
        for key, value in sorted(parts.items())
        if value is not None
    }
    digest = hashlib.sha256(repr(normalized).encode("utf-8")).hexdigest()[:24]
    return get_data_cache_dir() / namespace / f"{digest}.json"


def cached_result(
    *,
    namespace: str,
    ttl_seconds: int,
    loader: Callable[[], T],
    serializer: Callable[[T], dict],
    deserializer: Callable[[dict], T],
    cache_parts: dict[str, Any],
) -> T:
    """Load a result from cache or call loader and persist successful responses."""
    path = cache_path(namespace, **cache_parts)
    cached = load_json_cache_with_ttl(path, ttl_seconds=ttl_seconds)
    if isinstance(cached, dict):
        result = deserializer(cached)
        if hasattr(result, "quality"):
            quality = dict(getattr(result, "quality") or {})
            quality["cache_hit"] = True
            result = replace(result, quality=quality)
        return result

    result = loader()
    if getattr(result, "success", False):
        save_json_cache(path, serializer(result))
    return result


def actual_range_from_records(records: list[Any], date_attr: str) -> dict[str, str | None]:
    values = sorted(
        str(getattr(record, date_attr, "") or "")
        for record in records
        if getattr(record, date_attr, None)
    )
    return {
        "start_date": values[0] if values else None,
        "end_date": values[-1] if values else None,
    }


def missing_fields_from_records(records: list[Any], fields: list[str]) -> list[str]:
    missing: list[str] = []
    for field in fields:
        if not any(getattr(record, field, None) is not None for record in records):
            missing.append(field)
    return missing


def build_quality(
    *,
    provider: str,
    requested_start_date: str | None = None,
    requested_end_date: str | None = None,
    actual_start_date: str | None = None,
    actual_end_date: str | None = None,
    record_count: int = 0,
    fallback_used: bool = False,
    fallback_from: str | None = None,
    data_latency: str | None = None,
    missing_fields: list[str] | None = None,
    notes: list[str] | None = None,
) -> dict[str, Any]:
    return {
        "requested_range": {
            "start_date": requested_start_date,
            "end_date": requested_end_date,
        },
        "actual_range": {
            "start_date": actual_start_date,
            "end_date": actual_end_date,
        },
        "record_count": record_count,
        "source_provider": provider,
        "fallback_used": fallback_used,
        "fallback_from": fallback_from,
        "cache_hit": False,
        "as_of": datetime.now(timezone.utc).date().isoformat(),
        "data_latency": data_latency,
        "missing_fields": missing_fields or [],
        "notes": notes or [],
    }


def normalize_cn_code(symbol: str) -> str:
    value = symbol.strip().upper()
    if "." in value:
        return value.split(".", 1)[0]
    return re.sub(r"\D", "", value)
