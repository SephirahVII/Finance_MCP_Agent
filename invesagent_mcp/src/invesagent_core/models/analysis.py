from __future__ import annotations

from dataclasses import asdict, dataclass, field


@dataclass(frozen=True)
class PriceMetrics:
    """Price trend metrics for one instrument and period."""

    first_trade_time: str
    latest_trade_time: str
    first_close: float
    latest_close: float
    return_pct: float | None
    annual_volatility_pct: float | None
    max_drawdown_pct: float | None
    highest_price: float | None
    lowest_price: float | None
    average_amount: float | None
    ma5: float | None
    ma20: float | None
    ma60: float | None

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass(frozen=True)
class ExtremeDay:
    """Largest up or down day in an analysis period."""

    trade_time: str
    pct_chg: float | None
    close: float | None

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass(frozen=True)
class PriceTrendAnalysisResult:
    """Structured price trend analysis result."""

    success: bool
    symbol: str
    market: str
    asset_type: str
    provider: str
    start_date: str
    end_date: str
    trading_days: int
    metrics: PriceMetrics | None = None
    max_up: ExtremeDay | None = None
    max_down: ExtremeDay | None = None
    error_type: str | None = None
    message: str | None = None
    warnings: list[str] = field(default_factory=list)
    raw: dict | None = None

    def to_dict(self) -> dict:
        data = asdict(self)
        if self.metrics:
            data["metrics"] = self.metrics.to_dict()
        if self.max_up:
            data["max_up"] = self.max_up.to_dict()
        if self.max_down:
            data["max_down"] = self.max_down.to_dict()
        return data
