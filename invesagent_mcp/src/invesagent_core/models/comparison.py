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


@dataclass(frozen=True)
class MultiInstrumentComparisonItem:
    """Comparison metrics for one instrument in a peer group."""

    symbol: str
    market: str
    asset_type: str
    provider: str
    success: bool
    trading_days: int = 0
    latest_close: float | None = None
    return_pct: float | None = None
    annual_volatility_pct: float | None = None
    max_drawdown_pct: float | None = None
    rank_return: int | None = None
    rank_volatility: int | None = None
    rank_drawdown: int | None = None
    latest_pe_ttm: float | None = None
    latest_pb: float | None = None
    latest_total_mv: float | None = None
    latest_roe: float | None = None
    latest_gross_margin: float | None = None
    latest_net_profit_margin: float | None = None
    error_type: str | None = None
    message: str | None = None

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass(frozen=True)
class MultiInstrumentComparisonResult:
    """Unified horizontal comparison result for multiple instruments."""

    success: bool
    symbols: list[str]
    market: str
    asset_type: str
    provider: str
    start_date: str
    end_date: str
    items: list[MultiInstrumentComparisonItem] = field(default_factory=list)
    rankings: dict = field(default_factory=dict)
    correlation_matrix: dict | None = None
    error_type: str | None = None
    message: str | None = None
    warnings: list[str] = field(default_factory=list)
    raw: dict | None = None

    def to_dict(self) -> dict:
        data = asdict(self)
        data["items"] = [item.to_dict() for item in self.items]
        return data
