from __future__ import annotations

import math

import pandas as pd


def safe_round(value: float | None, digits: int = 4) -> float | None:
    """Round numeric values while preserving None and NaN as None."""
    if value is None:
        return None

    if isinstance(value, float) and math.isnan(value):
        return None

    return round(float(value), digits)


def calc_period_returns(close: pd.Series) -> pd.Series:
    """Calculate period-over-period returns from close prices."""
    return pd.to_numeric(close, errors="coerce").pct_change()


def calc_simple_return_pct(close: pd.Series) -> float | None:
    """Calculate interval return in percent."""
    series = pd.to_numeric(close, errors="coerce").dropna()

    if len(series) < 2:
        return None

    first = float(series.iloc[0])
    latest = float(series.iloc[-1])

    if first == 0:
        return None

    return safe_round((latest / first - 1) * 100)


def calc_annual_volatility_pct(
    returns: pd.Series,
    periods_per_year: int = 252,
) -> float | None:
    """Calculate annualized volatility in percent."""
    series = pd.to_numeric(returns, errors="coerce").dropna()

    if len(series) < 2:
        return None

    return safe_round(float(series.std() * math.sqrt(periods_per_year) * 100))


def calc_max_drawdown_pct(close: pd.Series) -> float | None:
    """Calculate max drawdown in percent."""
    series = pd.to_numeric(close, errors="coerce").dropna()

    if series.empty:
        return None

    running_max = series.cummax()
    drawdown = series / running_max - 1

    return safe_round(float(drawdown.min() * 100))


def calc_extreme_return_days(
    df: pd.DataFrame,
    return_column: str = "pct_chg",
    close_column: str = "close",
    time_column: str = "trade_time",
) -> tuple[dict | None, dict | None]:
    """Return max-up and max-down rows as dictionaries."""
    if df.empty or return_column not in df.columns:
        return None, None

    valid = df.dropna(subset=[return_column])

    if valid.empty:
        return None, None

    max_up_row = valid.loc[valid[return_column].idxmax()]
    max_down_row = valid.loc[valid[return_column].idxmin()]

    def to_item(row) -> dict:
        return {
            "trade_time": str(row[time_column]),
            "pct_chg": safe_round(float(row[return_column])),
            "close": safe_round(float(row[close_column])) if close_column in row else None,
        }

    return to_item(max_up_row), to_item(max_down_row)
