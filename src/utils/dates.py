from __future__ import annotations

import re


def normalize_yyyymmdd_date(value: str) -> str:
    """Normalize date input to YYYYMMDD.

    Supported inputs:
    - 20240101
    - 2024-01-01
    - 2024/01/01
    """
    if not value:
        return value

    text = value.strip()

    if re.fullmatch(r"\d{8}", text):
        return text

    normalized = text.replace("-", "").replace("/", "")

    if re.fullmatch(r"\d{8}", normalized):
        return normalized

    raise ValueError(
        f"Invalid date format: {value}. Expected YYYYMMDD, YYYY-MM-DD, or YYYY/MM/DD."
    )
