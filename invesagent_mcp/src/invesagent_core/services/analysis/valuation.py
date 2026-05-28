from __future__ import annotations

import math

import pandas as pd

from invesagent_core.models.valuation import (
    ValuationAnalysisResult,
    ValuationMetrics,
    ValuationRecord,
    ValuationResult,
)
from invesagent_core.services.data.valuation import get_valuation


def _safe_round(value: float | None, digits: int = 4) -> float | None:
    if value is None:
        return None

    if isinstance(value, float) and math.isnan(value):
        return None

    return round(float(value), digits)


def _records_to_df(records: list[ValuationRecord]) -> pd.DataFrame:
    data = [record.to_dict() for record in records]
    df = pd.DataFrame(data)

    if df.empty:
        return df

    df = df.sort_values("trade_time").reset_index(drop=True)

    for column in [
        "close",
        "turnover_rate",
        "turnover_rate_f",
        "volume_ratio",
        "pe",
        "pe_ttm",
        "pb",
        "ps",
        "ps_ttm",
        "dv_ratio",
        "dv_ttm",
        "total_mv",
        "circ_mv",
    ]:
        if column in df.columns:
            df[column] = pd.to_numeric(df[column], errors="coerce")

    return df


def _latest_valid(df: pd.DataFrame, column: str) -> float | None:
    if column not in df.columns:
        return None

    series = df[column].dropna()
    if series.empty:
        return None

    return _safe_round(float(series.iloc[-1]))


def _percentile_of_latest(df: pd.DataFrame, column: str) -> float | None:
    if column not in df.columns:
        return None

    series = df[column].dropna()
    if series.empty:
        return None

    latest = series.iloc[-1]
    percentile = (series <= latest).sum() / len(series) * 100
    return _safe_round(float(percentile))


def _change_pct(df: pd.DataFrame, column: str) -> float | None:
    if column not in df.columns:
        return None

    series = df[column].dropna()
    if len(series) < 2:
        return None

    first = float(series.iloc[0])
    latest = float(series.iloc[-1])

    if first == 0:
        return None

    return _safe_round((latest / first - 1) * 100)


def _recent_average(df: pd.DataFrame, column: str, window: int = 63) -> float | None:
    if column not in df.columns:
        return None

    series = df[column].dropna()
    if series.empty:
        return None

    return _safe_round(float(series.tail(window).mean()))


def analyze_valuation_from_result(
    valuation: ValuationResult,
) -> ValuationAnalysisResult:
    """Analyze unified valuation records."""
    if not valuation.success:
        return ValuationAnalysisResult(
            success=False,
            symbol=valuation.symbol,
            market=valuation.market,
            asset_type=valuation.asset_type,
            provider=valuation.provider,
            start_date=valuation.start_date,
            end_date=valuation.end_date,
            observations=0,
            error_type=valuation.error_type,
            message=valuation.message,
            warnings=valuation.warnings,
            raw=valuation.raw,
        )

    df = _records_to_df(valuation.records)

    if df.empty:
        return ValuationAnalysisResult(
            success=False,
            symbol=valuation.symbol,
            market=valuation.market,
            asset_type=valuation.asset_type,
            provider=valuation.provider,
            start_date=valuation.start_date,
            end_date=valuation.end_date,
            observations=0,
            error_type="empty_valuation_data",
            message="No valuation records available for analysis.",
        )

    warnings = list(valuation.warnings)

    if "pe_ttm" in df.columns and df["pe_ttm"].dropna().empty:
        warnings.append("PE TTM data is unavailable in the current valuation result.")

    if "pb" in df.columns and df["pb"].dropna().empty:
        warnings.append("PB data is unavailable in the current valuation result.")

    metrics = ValuationMetrics(
        first_trade_time=str(df.iloc[0]["trade_time"]),
        latest_trade_time=str(df.iloc[-1]["trade_time"]),
        latest_close=_latest_valid(df, "close"),
        latest_pe=_latest_valid(df, "pe"),
        latest_pe_ttm=_latest_valid(df, "pe_ttm"),
        latest_pb=_latest_valid(df, "pb"),
        latest_ps_ttm=_latest_valid(df, "ps_ttm"),
        latest_turnover_rate=_latest_valid(df, "turnover_rate"),
        three_month_avg_turnover_rate=_recent_average(df, "turnover_rate"),
        latest_total_share=_latest_valid(df, "total_share"),
        latest_float_share=_latest_valid(df, "float_share"),
        latest_total_mv=_latest_valid(df, "total_mv"),
        latest_circ_mv=_latest_valid(df, "circ_mv"),
        pe_ttm_percentile=_percentile_of_latest(df, "pe_ttm"),
        pb_percentile=_percentile_of_latest(df, "pb"),
        total_mv_change_pct=_change_pct(df, "total_mv"),
    )

    return ValuationAnalysisResult(
        success=True,
        symbol=valuation.symbol,
        market=valuation.market,
        asset_type=valuation.asset_type,
        provider=valuation.provider,
        start_date=valuation.start_date,
        end_date=valuation.end_date,
        observations=len(df),
        metrics=metrics,
        warnings=warnings,
    )


def analyze_valuation(
    symbol: str,
    market: str,
    start_date: str,
    end_date: str,
    asset_type: str = "stock",
    provider: str = "auto",
) -> ValuationAnalysisResult:
    """Fetch unified valuation data and analyze it."""
    valuation = get_valuation(
        symbol=symbol,
        market=market,
        asset_type=asset_type,
        start_date=start_date,
        end_date=end_date,
        provider=provider,
    )

    return analyze_valuation_from_result(valuation)
