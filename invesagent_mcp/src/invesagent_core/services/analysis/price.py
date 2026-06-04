from __future__ import annotations

import pandas as pd

from invesagent_core.models.analysis import ExtremeDay, PriceMetrics, PriceTrendAnalysisResult
from invesagent_core.models.market_data import MarketDataResult, OHLCVRecord
from invesagent_core.services.data.market_data import get_ohlcv
from invesagent_core.services.metrics.price import (
    calc_annual_volatility_pct,
    calc_extreme_return_days,
    calc_max_drawdown_pct,
    calc_period_returns,
    calc_simple_return_pct,
    safe_round,
)
from invesagent_core.services.metrics.technical import latest_moving_average


def _records_to_df(records: list[OHLCVRecord]) -> pd.DataFrame:
    """Convert OHLCV records to a sorted DataFrame."""
    data = [record.to_dict() for record in records]
    df = pd.DataFrame(data)

    if df.empty:
        return df

    df = df.sort_values("trade_time").reset_index(drop=True)

    for column in ["open", "high", "low", "close", "volume", "amount"]:
        if column in df.columns:
            df[column] = pd.to_numeric(df[column], errors="coerce")

    df["daily_return"] = calc_period_returns(df["close"])
    df["pct_chg"] = df["daily_return"] * 100

    return df


def analyze_ohlcv_price_trend_from_result(
    market_data: MarketDataResult,
) -> PriceTrendAnalysisResult:
    """Analyze price trend from a unified MarketDataResult."""
    if not market_data.success:
        return PriceTrendAnalysisResult(
            success=False,
            symbol=market_data.symbol,
            market=market_data.market,
            asset_type=market_data.asset_type,
            provider=market_data.provider,
            start_date=market_data.start_date,
            end_date=market_data.end_date,
            trading_days=0,
            error_type=market_data.error_type,
            message=market_data.message,
            warnings=market_data.warnings,
            raw=market_data.raw,
            quality=market_data.quality,
        )

    df = _records_to_df(market_data.records)

    if df.empty or "close" not in df.columns:
        return PriceTrendAnalysisResult(
            success=False,
            symbol=market_data.symbol,
            market=market_data.market,
            asset_type=market_data.asset_type,
            provider=market_data.provider,
            start_date=market_data.start_date,
            end_date=market_data.end_date,
            trading_days=0,
            error_type="empty_price_data",
            message="No OHLCV records available for price trend analysis.",
        )

    first_close = float(df.iloc[0]["close"])
    latest_close = float(df.iloc[-1]["close"])
    max_up_day, max_down_day = calc_extreme_return_days(df)

    warnings: list[str] = []
    warnings.extend(market_data.warnings)
    if len(df) < 60:
        warnings.append("Trading days fewer than 60; MA60 is unavailable or less meaningful.")

    metrics = PriceMetrics(
        first_trade_time=str(df.iloc[0]["trade_time"]),
        latest_trade_time=str(df.iloc[-1]["trade_time"]),
        first_close=safe_round(first_close),
        latest_close=safe_round(latest_close),
        return_pct=calc_simple_return_pct(df["close"]),
        annual_volatility_pct=calc_annual_volatility_pct(df["daily_return"]),
        max_drawdown_pct=calc_max_drawdown_pct(df["close"]),
        highest_price=safe_round(df["high"].max()) if "high" in df.columns else None,
        lowest_price=safe_round(df["low"].min()) if "low" in df.columns else None,
        average_amount=safe_round(df["amount"].mean()) if "amount" in df.columns else None,
        ma5=latest_moving_average(df["close"], 5),
        ma20=latest_moving_average(df["close"], 20),
        ma60=latest_moving_average(df["close"], 60),
    )

    max_up = (
        ExtremeDay(
            trade_time=str(max_up_day["trade_time"]),
            pct_chg=max_up_day["pct_chg"],
            close=max_up_day["close"],
        )
        if max_up_day is not None
        else None
    )

    max_down = (
        ExtremeDay(
            trade_time=str(max_down_day["trade_time"]),
            pct_chg=max_down_day["pct_chg"],
            close=max_down_day["close"],
        )
        if max_down_day is not None
        else None
    )

    return PriceTrendAnalysisResult(
        success=True,
        symbol=market_data.symbol,
        market=market_data.market,
        asset_type=market_data.asset_type,
        provider=market_data.provider,
        start_date=market_data.start_date,
        end_date=market_data.end_date,
        trading_days=len(df),
        metrics=metrics,
        max_up=max_up,
        max_down=max_down,
        warnings=warnings,
        quality=market_data.quality,
    )


def analyze_ohlcv_price_trend(
    symbol: str,
    market: str,
    start_date: str,
    end_date: str,
    asset_type: str = "stock",
    provider: str = "auto",
    frequency: str = "daily",
    adjust: str | None = None,
) -> PriceTrendAnalysisResult:
    """Fetch unified OHLCV data and analyze price trend."""
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

    return analyze_ohlcv_price_trend_from_result(market_data)
