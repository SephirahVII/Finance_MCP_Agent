from __future__ import annotations


def normalize_yyyymmdd_date(value: str | int | None) -> str:
    """Normalize YYYY-MM-DD, YYYY/MM/DD, or YYYYMMDD into YYYYMMDD."""
    if value is None:
        return ""
    text = str(value).strip()
    return text.replace("-", "").replace("/", "")
