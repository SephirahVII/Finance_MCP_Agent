from __future__ import annotations

from dataclasses import asdict, dataclass, field


@dataclass(frozen=True)
class FundamentalRecord:
    """Unified financial statement or indicator record."""

    symbol: str
    period: str | None = None
    ann_date: str | None = None
    report_type: str | None = None
    statement_type: str | None = None
    provider: str | None = None
    market: str | None = None
    asset_type: str | None = None
    raw: dict | None = None

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass(frozen=True)
class FundamentalsResult:
    """Unified financial fundamentals query result."""

    success: bool
    symbol: str
    start_date: str
    end_date: str
    provider: str
    market: str
    asset_type: str
    data_type: str
    records: list[FundamentalRecord] = field(default_factory=list)
    error_type: str | None = None
    message: str | None = None
    warnings: list[str] = field(default_factory=list)
    raw: dict | None = None

    def to_dict(self) -> dict:
        data = asdict(self)
        data["records"] = [record.to_dict() for record in self.records]
        return data


@dataclass(frozen=True)
class FundamentalsMetrics:
    """High-level metrics extracted from financial statements and indicators."""

    latest_period: str | None = None
    latest_revenue: float | None = None
    latest_net_profit: float | None = None
    latest_operating_cashflow: float | None = None
    latest_total_assets: float | None = None
    latest_total_liabilities: float | None = None
    latest_roe: float | None = None
    latest_gross_margin: float | None = None
    latest_net_profit_margin: float | None = None
    revenue_growth_pct: float | None = None
    net_profit_growth_pct: float | None = None
    debt_to_assets_pct: float | None = None
    operating_cashflow_to_profit: float | None = None

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass(frozen=True)
class FundamentalsAnalysisResult:
    """Unified fundamentals analysis result."""

    success: bool
    symbol: str
    market: str
    asset_type: str
    provider: str
    start_date: str
    end_date: str
    metrics: FundamentalsMetrics | None = None
    error_type: str | None = None
    message: str | None = None
    warnings: list[str] = field(default_factory=list)
    raw: dict | None = None

    def to_dict(self) -> dict:
        data = asdict(self)

        if self.metrics:
            data["metrics"] = self.metrics.to_dict()

        return data
