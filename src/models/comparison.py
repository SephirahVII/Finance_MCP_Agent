from __future__ import annotations

from dataclasses import asdict, dataclass, field


@dataclass(frozen=True)
class InstrumentComparisonMetrics:
    """Price and risk comparison metrics for two instruments."""

    primary_return_pct: float | None = None
    benchmark_return_pct: float | None = None
    excess_return_pct: float | None = None
    primary_volatility_pct: float | None = None
    benchmark_volatility_pct: float | None = None
    volatility_diff_pct: float | None = None
    primary_max_drawdown_pct: float | None = None
    benchmark_max_drawdown_pct: float | None = None
    correlation: float | None = None
    primary_trading_days: int = 0
    benchmark_trading_days: int = 0
    aligned_observations: int = 0

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass(frozen=True)
class InstrumentComparisonResult:
    """Unified comparison result for a primary instrument and a benchmark."""

    success: bool
    primary_symbol: str
    benchmark_symbol: str
    market: str
    provider: str
    start_date: str
    end_date: str
    primary_asset_type: str
    benchmark_asset_type: str
    metrics: InstrumentComparisonMetrics | None = None
    error_type: str | None = None
    message: str | None = None
    warnings: list[str] = field(default_factory=list)
    raw: dict | None = None

    def to_dict(self) -> dict:
        data = asdict(self)

        if self.metrics:
            data["metrics"] = self.metrics.to_dict()

        return data
