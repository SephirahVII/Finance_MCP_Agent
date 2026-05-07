from __future__ import annotations

import pandas as pd

from src.models.comparison import InstrumentComparisonMetrics, InstrumentComparisonResult
from src.models.market_data import MarketDataResult, OHLCVRecord
from src.services.analysis.price import analyze_ohlcv_price_trend_from_result
from src.services.data.market_data import get_ohlcv
from src.services.metrics.multivariate import (
    align_returns_by_time,
    calc_correlation,
    calc_difference,
    calc_excess_return_pct,
)
from src.services.metrics.price import calc_period_returns
from src.utils.dates import normalize_yyyymmdd_date


def _records_to_returns_df(records: list[OHLCVRecord], prefix: str) -> pd.DataFrame:
    data = [record.to_dict() for record in records]
    df = pd.DataFrame(data)

    if df.empty:
        return df

    df = df.sort_values("trade_time").reset_index(drop=True)
    df["close"] = pd.to_numeric(df["close"], errors="coerce")
    df[f"{prefix}_return"] = calc_period_returns(df["close"])

    return df[["trade_time", f"{prefix}_return"]]


def _failed_result(
    primary_data: MarketDataResult,
    benchmark_data: MarketDataResult,
    primary_asset_type: str,
    benchmark_asset_type: str,
    provider: str,
) -> InstrumentComparisonResult:
    warnings: list[str] = []

    if not primary_data.success:
        warnings.append(f"primary unavailable: {primary_data.error_type or primary_data.message}")

    if not benchmark_data.success:
        warnings.append(f"benchmark unavailable: {benchmark_data.error_type or benchmark_data.message}")

    return InstrumentComparisonResult(
        success=False,
        primary_symbol=primary_data.symbol,
        benchmark_symbol=benchmark_data.symbol,
        market=primary_data.market,
        provider=provider,
        start_date=primary_data.start_date,
        end_date=primary_data.end_date,
        primary_asset_type=primary_asset_type,
        benchmark_asset_type=benchmark_asset_type,
        error_type="market_data_unavailable",
        message="Primary or benchmark market data is unavailable.",
        warnings=warnings,
        raw={
            "primary": primary_data.to_dict(),
            "benchmark": benchmark_data.to_dict(),
        },
    )


def compare_ohlcv_with_benchmark(
    primary_symbol: str,
    benchmark_symbol: str,
    market: str,
    start_date: str,
    end_date: str,
    primary_asset_type: str = "stock",
    benchmark_asset_type: str = "index",
    provider: str = "auto",
    frequency: str = "daily",
    adjust: str | None = None,
) -> InstrumentComparisonResult:
    """Compare price performance between one instrument and a benchmark."""
    start_date = normalize_yyyymmdd_date(start_date)
    end_date = normalize_yyyymmdd_date(end_date)

    primary_data = get_ohlcv(
        symbol=primary_symbol,
        market=market,
        asset_type=primary_asset_type,
        start_date=start_date,
        end_date=end_date,
        provider=provider,
        frequency=frequency,
        adjust=adjust,
    )
    benchmark_data = get_ohlcv(
        symbol=benchmark_symbol,
        market=market,
        asset_type=benchmark_asset_type,
        start_date=start_date,
        end_date=end_date,
        provider=provider,
        frequency=frequency,
        adjust=None,
    )

    if not primary_data.success or not benchmark_data.success:
        return _failed_result(
            primary_data=primary_data,
            benchmark_data=benchmark_data,
            primary_asset_type=primary_asset_type,
            benchmark_asset_type=benchmark_asset_type,
            provider=provider,
        )

    primary_analysis = analyze_ohlcv_price_trend_from_result(primary_data)
    benchmark_analysis = analyze_ohlcv_price_trend_from_result(benchmark_data)

    primary_returns = _records_to_returns_df(primary_data.records, "primary")
    benchmark_returns = _records_to_returns_df(benchmark_data.records, "benchmark")

    aligned = align_returns_by_time(primary_returns, benchmark_returns)
    correlation = calc_correlation(aligned["primary_return"], aligned["benchmark_return"])

    primary_metrics = primary_analysis.metrics
    benchmark_metrics = benchmark_analysis.metrics

    primary_return = primary_metrics.return_pct if primary_metrics else None
    benchmark_return = benchmark_metrics.return_pct if benchmark_metrics else None
    primary_volatility = primary_metrics.annual_volatility_pct if primary_metrics else None
    benchmark_volatility = benchmark_metrics.annual_volatility_pct if benchmark_metrics else None

    metrics = InstrumentComparisonMetrics(
        primary_return_pct=primary_return,
        benchmark_return_pct=benchmark_return,
        excess_return_pct=calc_excess_return_pct(primary_return, benchmark_return),
        primary_volatility_pct=primary_volatility,
        benchmark_volatility_pct=benchmark_volatility,
        volatility_diff_pct=calc_difference(primary_volatility, benchmark_volatility),
        primary_max_drawdown_pct=primary_metrics.max_drawdown_pct if primary_metrics else None,
        benchmark_max_drawdown_pct=benchmark_metrics.max_drawdown_pct if benchmark_metrics else None,
        correlation=correlation,
        primary_trading_days=primary_analysis.trading_days,
        benchmark_trading_days=benchmark_analysis.trading_days,
        aligned_observations=len(aligned),
    )

    return InstrumentComparisonResult(
        success=True,
        primary_symbol=primary_symbol,
        benchmark_symbol=benchmark_symbol,
        market=market,
        provider="tushare" if provider == "auto" else provider,
        start_date=start_date,
        end_date=end_date,
        primary_asset_type=primary_asset_type,
        benchmark_asset_type=benchmark_asset_type,
        metrics=metrics,
        warnings=primary_analysis.warnings + benchmark_analysis.warnings,
    )
