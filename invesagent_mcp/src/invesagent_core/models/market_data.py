from __future__ import annotations

from dataclasses import asdict, dataclass, field


@dataclass(frozen=True)
class OHLCVRecord:
    """One normalized OHLCV bar."""

    symbol: str
    trade_time: str
    open: float
    high: float
    low: float
    close: float
    volume: float | None = None
    amount: float | None = None
    provider: str | None = None
    market: str | None = None
    asset_type: str | None = None
    raw: dict | None = None

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass(frozen=True)
class MarketDataResult:
    """Normalized market data response."""

    success: bool
    symbol: str
    start_date: str
    end_date: str
    provider: str
    market: str
    asset_type: str
    records: list[OHLCVRecord] = field(default_factory=list)
    error_type: str | None = None
    message: str | None = None
    warnings: list[str] = field(default_factory=list)
    raw: dict | None = None

    def to_dict(self) -> dict:
        data = asdict(self)
        data["records"] = [record.to_dict() for record in self.records]
        return data
