from __future__ import annotations

import json
from pathlib import Path
from time import time
from typing import Any


def load_json_cache(path: Path) -> Any | None:
    """Load JSON cache if it exists."""
    if not path.exists():
        return None

    with path.open("r", encoding="utf-8") as file:
        return json.load(file)


def save_json_cache(path: Path, data: Any) -> None:
    """Save data to a JSON cache file."""
    path.parent.mkdir(parents=True, exist_ok=True)

    with path.open("w", encoding="utf-8") as file:
        json.dump(data, file, ensure_ascii=False, indent=2)


def load_json_cache_with_ttl(path: Path, ttl_seconds: int | None = None) -> Any | None:
    """Load JSON cache when present and fresh enough."""
    if not path.exists():
        return None

    if ttl_seconds is not None and ttl_seconds >= 0:
        age = time() - path.stat().st_mtime
        if age > ttl_seconds:
            return None

    return load_json_cache(path)
