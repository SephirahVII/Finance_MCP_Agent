from __future__ import annotations

import math

from invesagent_core.models.fundamentals import (
    FundamentalRecord,
    FundamentalsAnalysisResult,
    FundamentalsMetrics,
)
from invesagent_core.services.data.fundamentals import get_fundamentals
from invesagent_core.utils.dates import normalize_yyyymmdd_date


def _safe_float(value) -> float | None:
    if value is None or value == "":
        return None

    try:
        converted = float(value)
    except (TypeError, ValueError):
        return None

    if math.isnan(converted):
        return None

    return converted


def _safe_round(value: float | None, digits: int = 4) -> float | None:
    if value is None:
        return None
    return round(float(value), digits)


def _latest_record(records: list[FundamentalRecord]) -> FundamentalRecord | None:
    if not records:
        return None
    return sorted(records, key=lambda record: record.period or "")[-1]


def _first_and_latest_values(
    records: list[FundamentalRecord],
    field: str,
) -> tuple[float | None, float | None]:
    values: list[float] = []

    for record in sorted(records, key=lambda item: item.period or ""):
        raw = record.raw or {}
        value = _safe_float(raw.get(field))
        if value is not None:
            values.append(value)

    if not values:
        return None, None

    return values[0], values[-1]


def _growth_pct(records: list[FundamentalRecord], field: str) -> float | None:
    first, latest = _first_and_latest_values(records, field)

    if first in (None, 0) or latest is None:
        return None

    return _safe_round((latest / first - 1) * 100)


def analyze_fundamentals(
    symbol: str,
    market: str,
    start_date: str,
    end_date: str,
    asset_type: str = "stock",
    provider: str = "auto",
) -> FundamentalsAnalysisResult:
    """Fetch and summarize key income, balance sheet, cashflow, and indicator data."""
    income = get_fundamentals(
        symbol=symbol,
        market=market,
        asset_type=asset_type,
        data_type="income",
        start_date=start_date,
        end_date=end_date,
        provider=provider,
    )
    balance = get_fundamentals(
        symbol=symbol,
        market=market,
        asset_type=asset_type,
        data_type="balancesheet",
        start_date=start_date,
        end_date=end_date,
        provider=provider,
    )
    cashflow = get_fundamentals(
        symbol=symbol,
        market=market,
        asset_type=asset_type,
        data_type="cashflow",
        start_date=start_date,
        end_date=end_date,
        provider=provider,
    )
    indicators = get_fundamentals(
        symbol=symbol,
        market=market,
        asset_type=asset_type,
        data_type="fina_indicator",
        start_date=start_date,
        end_date=end_date,
        provider=provider,
    )

    results = {
        "income": income,
        "balancesheet": balance,
        "cashflow": cashflow,
        "fina_indicator": indicators,
    }

    warnings: list[str] = []
    for name, result in results.items():
        if not result.success:
            warnings.append(f"{name} unavailable: {result.error_type or result.message}")

    if not any(result.success for result in results.values()):
        first_error = next(iter(results.values()))
        return FundamentalsAnalysisResult(
            success=False,
            symbol=symbol,
            market=market,
            asset_type=asset_type,
            provider=provider,
            start_date=normalize_yyyymmdd_date(start_date),
            end_date=normalize_yyyymmdd_date(end_date),
            error_type=first_error.error_type,
            message="No fundamentals data available for analysis.",
            warnings=warnings,
            raw={key: value.to_dict() for key, value in results.items()},
        )

    latest_income = _latest_record(income.records) if income.success else None
    latest_balance = _latest_record(balance.records) if balance.success else None
    latest_cashflow = _latest_record(cashflow.records) if cashflow.success else None
    latest_indicator = _latest_record(indicators.records) if indicators.success else None

    income_raw = latest_income.raw if latest_income else {}
    balance_raw = latest_balance.raw if latest_balance else {}
    cashflow_raw = latest_cashflow.raw if latest_cashflow else {}
    indicator_raw = latest_indicator.raw if latest_indicator else {}

    latest_assets = _safe_float(balance_raw.get("total_assets"))
    latest_liabilities = _safe_float(balance_raw.get("total_liab"))
    latest_net_profit = _safe_float(income_raw.get("n_income_attr_p")) or _safe_float(
        income_raw.get("n_income")
    )
    latest_ocf = _safe_float(cashflow_raw.get("n_cashflow_act"))

    debt_to_assets_pct = None
    if latest_assets not in (None, 0) and latest_liabilities is not None:
        debt_to_assets_pct = _safe_round(latest_liabilities / latest_assets * 100)

    operating_cashflow_to_profit = None
    if latest_net_profit not in (None, 0) and latest_ocf is not None:
        operating_cashflow_to_profit = _safe_round(latest_ocf / latest_net_profit)

    latest_period = None
    for record in [latest_income, latest_balance, latest_cashflow, latest_indicator]:
        if record and record.period:
            latest_period = record.period

    metrics = FundamentalsMetrics(
        latest_period=latest_period,
        latest_revenue=_safe_round(_safe_float(income_raw.get("revenue"))),
        latest_net_profit=_safe_round(latest_net_profit),
        latest_operating_cashflow=_safe_round(latest_ocf),
        latest_total_assets=_safe_round(latest_assets),
        latest_total_liabilities=_safe_round(latest_liabilities),
        latest_roe=_safe_round(
            _safe_float(indicator_raw.get("roe"))
            or _safe_float(indicator_raw.get("roe_dt"))
        ),
        latest_gross_margin=_safe_round(_safe_float(indicator_raw.get("grossprofit_margin"))),
        latest_net_profit_margin=_safe_round(_safe_float(indicator_raw.get("netprofit_margin"))),
        revenue_growth_pct=_growth_pct(income.records, "revenue") if income.success else None,
        net_profit_growth_pct=_growth_pct(income.records, "n_income_attr_p") if income.success else None,
        debt_to_assets_pct=debt_to_assets_pct,
        operating_cashflow_to_profit=operating_cashflow_to_profit,
    )

    return FundamentalsAnalysisResult(
        success=True,
        symbol=symbol,
        market=market,
        asset_type=asset_type,
        provider="tushare" if provider == "auto" else provider,
        start_date=normalize_yyyymmdd_date(start_date),
        end_date=normalize_yyyymmdd_date(end_date),
        metrics=metrics,
        warnings=warnings,
        raw={key: value.to_dict() for key, value in results.items()},
    )
