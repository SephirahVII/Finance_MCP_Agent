from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass(frozen=True)
class AlternativeDataRecord:
    """One normalized record for non-OHLCV financial datasets."""

    category: str
    symbol: str | None = None
    date: str | None = None
    end_date: str | None = None
    name: str | None = None
    title: str | None = None
    value: float | str | None = None
    unit: str | None = None
    metrics: dict[str, Any] = field(default_factory=dict)
    url: str | None = None
    provider: str | None = None
    market: str | None = None
    raw: dict[str, Any] | None = None

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass(frozen=True)
class AlternativeDataResult:
    """Unified result for announcements, holders, capital flows, macro data, etc."""

    success: bool
    category: str
    provider: str
    market: str
    symbol: str | None = None
    start_date: str | None = None
    end_date: str | None = None
    records: list[AlternativeDataRecord] = field(default_factory=list)
    error_type: str | None = None
    message: str | None = None
    warnings: list[str] = field(default_factory=list)
    raw: dict[str, Any] | None = None
    quality: dict[str, Any] | None = None

    def to_dict(self) -> dict:
        data = asdict(self)
        data["records"] = [record.to_dict() for record in self.records]
        return data
