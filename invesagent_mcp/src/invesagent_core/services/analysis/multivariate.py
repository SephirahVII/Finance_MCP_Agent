from __future__ import annotations

import pandas as pd

from invesagent_core.models.comparison import (
    InstrumentComparisonMetrics,
    InstrumentComparisonResult,
    MultiInstrumentComparisonItem,
    MultiInstrumentComparisonResult,
)
from invesagent_core.models.market_data import MarketDataResult, OHLCVRecord
from invesagent_core.services.analysis.price import analyze_ohlcv_price_trend_from_result
from invesagent_core.services.analysis.valuation import analyze_valuation
from invesagent_core.services.analysis.fundamentals import analyze_fundamentals
from invesagent_core.services.data.market_data import get_ohlcv
from invesagent_core.services.metrics.multivariate import (
    align_returns_by_time,
    calc_correlation,
    calc_difference,
    calc_excess_return_pct,
)
from invesagent_core.services.metrics.price import calc_period_returns
from invesagent_core.utils.dates import normalize_yyyymmdd_date


def _records_to_returns_df(records: list[OHLCVRecord], prefix: str) -> pd.DataFrame:
    data = [record.to_dict() for record in records]
    df = pd.DataFrame(data)

    if df.empty:
        return df

    df = df.sort_values("trade_time").reset_index(drop=True)
    df["close"] = pd.to_numeric(df["close"], errors="coerce")
    df[f"{prefix}_return"] = calc_period_returns(df["close"])

    return df[["trade_time", f"{prefix}_return"]]


def _records_to_named_returns_df(records: list[OHLCVRecord], symbol: str) -> pd.DataFrame:
    data = [record.to_dict() for record in records]
    df = pd.DataFrame(data)

    if df.empty:
        return df

    df = df.sort_values("trade_time").reset_index(drop=True)
    df["close"] = pd.to_numeric(df["close"], errors="coerce")
    df[symbol] = calc_period_returns(df["close"])

    return df[["trade_time", symbol]]


def _parse_symbols(symbols: list[str] | str) -> list[str]:
    if isinstance(symbols, str):
        values = symbols.replace("\uFF0C", ",").split(",")
    else:
        values = symbols

    parsed = [str(value).strip() for value in values if str(value).strip()]
    return list(dict.fromkeys(parsed))


def _rank_items(
    items: list[MultiInstrumentComparisonItem],
    field: str,
    descending: bool = True,
) -> dict[str, int]:
    valid_items = [
        item
        for item in items
        if item.success and getattr(item, field) is not None
    ]
    valid_items = sorted(
        valid_items,
        key=lambda item: getattr(item, field),
        reverse=descending,
    )

    return {item.symbol: index + 1 for index, item in enumerate(valid_items)}


def _build_correlation_matrix(return_frames: list[pd.DataFrame]) -> dict | None:
    if len(return_frames) < 2:
        return None

    merged = return_frames[0]
    for frame in return_frames[1:]:
        merged = pd.merge(merged, frame, on="trade_time", how="inner")

    if len(merged) < 2:
        return None

    corr = merged.drop(columns=["trade_time"]).corr()
    return {
        row: {
            column: None if pd.isna(value) else round(float(value), 4)
            for column, value in values.items()
        }
        for row, values in corr.to_dict(orient="index").items()
    }


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


def compare_ohlcv_instruments(
    symbols: list[str] | str,
    market: str,
    start_date: str,
    end_date: str,
    asset_type: str = "stock",
    provider: str = "auto",
    frequency: str = "daily",
    adjust: str | None = None,
    include_correlation: bool = True,
    include_valuation: bool = False,
    include_fundamentals: bool = False,
) -> MultiInstrumentComparisonResult:
    """Compare OHLCV performance across multiple instruments."""
    parsed_symbols = _parse_symbols(symbols)
    start_date = normalize_yyyymmdd_date(start_date)
    end_date = normalize_yyyymmdd_date(end_date)

    if len(parsed_symbols) < 2:
        return MultiInstrumentComparisonResult(
            success=False,
            symbols=parsed_symbols,
            market=market,
            asset_type=asset_type,
            provider=provider,
            start_date=start_date,
            end_date=end_date,
            error_type="insufficient_symbols",
            message="At least two symbols are required for multi-instrument comparison.",
        )

    items: list[MultiInstrumentComparisonItem] = []
    warnings: list[str] = []
    raw_results: dict = {}
    return_frames: list[pd.DataFrame] = []

    for symbol in parsed_symbols:
        market_data = get_ohlcv(
            symbol=symbol,
            market=market,
            asset_type=asset_type,
            start_date=start_date,
            end_date=end_date,
            provider=provider,
            frequency=frequency,
            adjust=adjust,
        )
        raw_results[symbol] = market_data.to_dict()

        if not market_data.success:
            items.append(
                MultiInstrumentComparisonItem(
                    symbol=symbol,
                    market=market,
                    asset_type=asset_type,
                    provider=market_data.provider,
                    success=False,
                    error_type=market_data.error_type,
                    message=market_data.message,
                )
            )
            warnings.append(f"{symbol} unavailable: {market_data.error_type or market_data.message}")
            continue

        analysis = analyze_ohlcv_price_trend_from_result(market_data)
        metrics = analysis.metrics

        items.append(
            _build_multi_item(
                symbol=symbol,
                market=market_data.market,
                asset_type=market_data.asset_type,
                provider=market_data.provider,
                success=True,
                trading_days=analysis.trading_days,
                latest_close=metrics.latest_close if metrics else None,
                return_pct=metrics.return_pct if metrics else None,
                annual_volatility_pct=metrics.annual_volatility_pct if metrics else None,
                max_drawdown_pct=metrics.max_drawdown_pct if metrics else None,
                start_date=start_date,
                end_date=end_date,
                include_valuation=include_valuation,
                include_fundamentals=include_fundamentals,
            )
        )
        warnings.extend([f"{symbol}: {warning}" for warning in analysis.warnings])

        if include_correlation:
            returns = _records_to_named_returns_df(market_data.records, symbol)
            if not returns.empty:
                return_frames.append(returns)

    success_items = [item for item in items if item.success]

    if len(success_items) < 2:
        return MultiInstrumentComparisonResult(
            success=False,
            symbols=parsed_symbols,
            market=market,
            asset_type=asset_type,
            provider=provider,
            start_date=start_date,
            end_date=end_date,
            items=items,
            error_type="insufficient_successful_data",
            message="Fewer than two instruments returned usable OHLCV data.",
            warnings=warnings,
            raw=raw_results,
        )

    return_ranks = _rank_items(items, "return_pct", descending=True)
    volatility_ranks = _rank_items(items, "annual_volatility_pct", descending=False)
    drawdown_ranks = _rank_items(items, "max_drawdown_pct", descending=True)

    ranked_items = [
        MultiInstrumentComparisonItem(
            symbol=item.symbol,
            market=item.market,
            asset_type=item.asset_type,
            provider=item.provider,
            success=item.success,
            trading_days=item.trading_days,
            latest_close=item.latest_close,
            return_pct=item.return_pct,
            annual_volatility_pct=item.annual_volatility_pct,
            max_drawdown_pct=item.max_drawdown_pct,
            rank_return=return_ranks.get(item.symbol),
            rank_volatility=volatility_ranks.get(item.symbol),
            rank_drawdown=drawdown_ranks.get(item.symbol),
            latest_pe_ttm=item.latest_pe_ttm,
            latest_pb=item.latest_pb,
            latest_total_mv=item.latest_total_mv,
            latest_roe=item.latest_roe,
            latest_gross_margin=item.latest_gross_margin,
            latest_net_profit_margin=item.latest_net_profit_margin,
            error_type=item.error_type,
            message=item.message,
        )
        for item in items
    ]

    rankings = {
        "by_return": sorted(return_ranks, key=return_ranks.get),
        "by_low_volatility": sorted(volatility_ranks, key=volatility_ranks.get),
        "by_low_drawdown": sorted(drawdown_ranks, key=drawdown_ranks.get),
    }

    return MultiInstrumentComparisonResult(
        success=True,
        symbols=parsed_symbols,
        market=market,
        asset_type=asset_type,
        provider=provider,
        start_date=start_date,
        end_date=end_date,
        items=ranked_items,
        rankings=rankings,
        correlation_matrix=_build_correlation_matrix(return_frames) if include_correlation else None,
        warnings=warnings,
        raw=raw_results,
    )


def _build_multi_item(
    symbol: str,
    market: str,
    asset_type: str,
    provider: str,
    success: bool,
    trading_days: int,
    latest_close: float | None,
    return_pct: float | None,
    annual_volatility_pct: float | None,
    max_drawdown_pct: float | None,
    start_date: str,
    end_date: str,
    include_valuation: bool,
    include_fundamentals: bool,
) -> MultiInstrumentComparisonItem:
    """Build one multi-instrument comparison item with optional enrichment."""
    latest_pe_ttm = None
    latest_pb = None
    latest_total_mv = None
    latest_roe = None
    latest_gross_margin = None
    latest_net_profit_margin = None

    if include_valuation:
        valuation = analyze_valuation(
            symbol=symbol,
            market=market,
            asset_type=asset_type,
            start_date=start_date,
            end_date=end_date,
            provider=provider,
        )
        if valuation.success and valuation.metrics:
            latest_pe_ttm = valuation.metrics.latest_pe_ttm
            latest_pb = valuation.metrics.latest_pb
            latest_total_mv = valuation.metrics.latest_total_mv

    if include_fundamentals:
        fundamentals = analyze_fundamentals(
            symbol=symbol,
            market=market,
            asset_type=asset_type,
            start_date=start_date,
            end_date=end_date,
            provider=provider,
        )
        if fundamentals.success and fundamentals.metrics:
            latest_roe = fundamentals.metrics.latest_roe
            latest_gross_margin = fundamentals.metrics.latest_gross_margin
            latest_net_profit_margin = fundamentals.metrics.latest_net_profit_margin

    return MultiInstrumentComparisonItem(
        symbol=symbol,
        market=market,
        asset_type=asset_type,
        provider=provider,
        success=success,
        trading_days=trading_days,
        latest_close=latest_close,
        return_pct=return_pct,
        annual_volatility_pct=annual_volatility_pct,
        max_drawdown_pct=max_drawdown_pct,
        latest_pe_ttm=latest_pe_ttm,
        latest_pb=latest_pb,
        latest_total_mv=latest_total_mv,
        latest_roe=latest_roe,
        latest_gross_margin=latest_gross_margin,
        latest_net_profit_margin=latest_net_profit_margin,
    )
