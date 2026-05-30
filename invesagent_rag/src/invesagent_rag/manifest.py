from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


@dataclass
class Manifest:
    path: Path
    records: dict[str, dict[str, Any]] = field(default_factory=dict)

    @classmethod
    def load(cls, path: Path) -> "Manifest":
        if not path.exists():
            return cls(path=path)
        return cls(path=path, records=json.loads(path.read_text(encoding="utf-8")))

    def is_current(self, relative_path: str, md5: str) -> bool:
        return self.records.get(relative_path, {}).get("md5") == md5

    def mark_ingested(self, relative_path: str, md5: str, chunks: int) -> None:
        self.records[relative_path] = {
            "md5": md5,
            "chunks": chunks,
            "ingested_at": datetime.now(timezone.utc).isoformat(),
        }

    def save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(
            json.dumps(self.records, ensure_ascii=False, indent=2, sort_keys=True),
            encoding="utf-8",
        )
