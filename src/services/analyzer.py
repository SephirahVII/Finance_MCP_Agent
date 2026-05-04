from __future__ import annotations

import math

import pandas as pd

from src.services.market_data import get_daily_prices


def _records_to_price_df(records: list[dict]) -> pd.DataFrame:
    """Convert daily price records to a sorted DataFrame."""
    df = pd.DataFrame(records)

    if df.empty:
        return df

    df = df.sort_values("trade_date").reset_index(drop=True)

    numeric_columns = [
        "open",
        "high",
        "low",
        "close",
        "pre_close",
        "change",
        "pct_chg",
        "vol",
        "amount",
    ]

    for column in numeric_columns:
        if column in df.columns:
            df[column] = pd.to_numeric(df[column], errors="coerce")

    return df

def _calc_max_drawdown(close_series: pd.Series) -> float | None:
    """Calculate max drawdown in percent."""
    if close_series.empty:
        return None

    running_max = close_series.cummax()
    drawdown = close_series / running_max - 1

    return round(float(drawdown.min() * 100), 4)

def _safe_round(value: float | None, digits: int = 4) -> float | None:
    """Round a value if it is not None or NaN."""
    if value is None:
        return None

    if isinstance(value, float) and math.isnan(value):
        return None

    return round(float(value), digits)

def analyze_price_trend(
    name_or_code: str,
    start_date: str,
    end_date: str,
) -> dict:
    """Analyze stock price trend using daily price data."""
    prices = get_daily_prices(
        name_or_code=name_or_code,
        start_date=start_date,
        end_date=end_date,
        limit=None,
    )

    if not prices.get("success"):
        return {
            "success": False,
            "error_type": prices.get("error_type", "price_data_unavailable"),
            "message": prices.get("message", "未能获取日线行情数据。"),
            "source": prices,
        }

    df = _records_to_price_df(prices["data"])

    if df.empty or "close" not in df.columns:
        return {
            "success": False,
            "error_type": "empty_price_data",
            "message": "日线行情数据为空，无法计算价格指标。",
            "source": prices,
        }

    first_close = float(df.iloc[0]["close"])
    latest_close = float(df.iloc[-1]["close"])
    return_pct = (latest_close / first_close - 1) * 100

    daily_return = df["close"].pct_change()
    annual_volatility_pct = daily_return.std() * math.sqrt(252) * 100

    max_drawdown_pct = _calc_max_drawdown(df["close"])

    ma_windows = [5, 20, 60]
    ma_values = {}
    for window in ma_windows:
        if len(df) >= window:
            ma_values[f"ma{window}"] = _safe_round(df["close"].rolling(window).mean().iloc[-1])
        else:
            ma_values[f"ma{window}"] = None

    max_up_day = df.loc[df["pct_chg"].idxmax()] if "pct_chg" in df.columns else None
    max_down_day = df.loc[df["pct_chg"].idxmin()] if "pct_chg" in df.columns else None

    result = {
        "success": True,
        "analysis_type": "price_trend",
        "ts_code": prices["ts_code"],
        "name": prices.get("name"),
        "start_date": start_date,
        "end_date": end_date,
        "trading_days": len(df),
        "metrics": {
            "first_trade_date": str(df.iloc[0]["trade_date"]),
            "latest_trade_date": str(df.iloc[-1]["trade_date"]),
            "first_close": _safe_round(first_close),
            "latest_close": _safe_round(latest_close),
            "return_pct": _safe_round(return_pct),
            "annual_volatility_pct": _safe_round(annual_volatility_pct),
            "max_drawdown_pct": max_drawdown_pct,
            "highest_price": _safe_round(df["high"].max()) if "high" in df.columns else None,
            "lowest_price": _safe_round(df["low"].min()) if "low" in df.columns else None,
            "average_amount": _safe_round(df["amount"].mean()) if "amount" in df.columns else None,
            **ma_values,
        },
        "extreme_days": {
            "max_up": {
                "trade_date": str(max_up_day["trade_date"]),
                "pct_chg": _safe_round(max_up_day["pct_chg"]),
                "close": _safe_round(max_up_day["close"]),
            }
            if max_up_day is not None
            else None,
            "max_down": {
                "trade_date": str(max_down_day["trade_date"]),
                "pct_chg": _safe_round(max_down_day["pct_chg"]),
                "close": _safe_round(max_down_day["close"]),
            }
            if max_down_day is not None
            else None,
        },
        "warnings": [],
    }

    if len(df) < 60:
        result["warnings"].append("交易日数量不足 60，MA60 无法计算或参考意义有限。")

    return result