from __future__ import annotations

from dataclasses import asdict, dataclass, field


@dataclass(frozen=True)
class ValuationRecord:
    """Unified daily valuation and trading-metric record."""

    symbol: str
    trade_time: str
    close: float | None = None
    turnover_rate: float | None = None
    turnover_rate_f: float | None = None
    volume_ratio: float | None = None
    pe: float | None = None
    pe_ttm: float | None = None
    pb: float | None = None
    ps: float | None = None
    ps_ttm: float | None = None
    dv_ratio: float | None = None
    dv_ttm: float | None = None
    total_share: float | None = None
    float_share: float | None = None
    free_share: float | None = None
    total_mv: float | None = None
    circ_mv: float | None = None
    provider: str | None = None
    market: str | None = None
    asset_type: str | None = None
    raw: dict | None = None

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass(frozen=True)
class ValuationResult:
    """Unified valuation query result."""

    success: bool
    symbol: str
    start_date: str
    end_date: str
    provider: str
    market: str
    asset_type: str
    records: list[ValuationRecord] = field(default_factory=list)
    error_type: str | None = None
    message: str | None = None
    warnings: list[str] = field(default_factory=list)
    raw: dict | None = None
    quality: dict | None = None

    def to_dict(self) -> dict:
        data = asdict(self)
        data["records"] = [record.to_dict() for record in self.records]
        return data


@dataclass(frozen=True)
class ValuationMetrics:
    """Summary metrics derived from valuation records."""

    first_trade_time: str | None
    latest_trade_time: str | None
    latest_close: float | None
    latest_pe: float | None
    latest_pe_ttm: float | None
    latest_pb: float | None
    latest_ps_ttm: float | None
    latest_turnover_rate: float | None
    three_month_avg_turnover_rate: float | None
    latest_total_share: float | None
    latest_float_share: float | None
    latest_total_mv: float | None
    latest_circ_mv: float | None
    pe_ttm_percentile: float | None
    pb_percentile: float | None
    total_mv_change_pct: float | None

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass(frozen=True)
class ValuationAnalysisResult:
    """Unified valuation analysis result."""

    success: bool
    symbol: str
    market: str
    asset_type: str
    provider: str
    start_date: str
    end_date: str
    observations: int
    metrics: ValuationMetrics | None = None
    error_type: str | None = None
    message: str | None = None
    warnings: list[str] = field(default_factory=list)
    raw: dict | None = None
    quality: dict | None = None

    def to_dict(self) -> dict:
        data = asdict(self)

        if self.metrics:
            data["metrics"] = self.metrics.to_dict()

        return data
