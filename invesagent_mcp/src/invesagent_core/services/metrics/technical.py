from __future__ import annotations

from collections.abc import Iterable

import pandas as pd


def parse_windows(windows: Iterable[int] | str | None, default: list[int] | None = None) -> list[int]:
    """Normalize window configuration from list-like or comma-separated strings."""
    if windows is None:
        return default or []

    if isinstance(windows, str):
        if not windows.strip():
            return []

        values = windows.replace("\uFF0C", ",").split(",")
        parsed = [int(value.strip()) for value in values if value.strip()]
    else:
        parsed = [int(value) for value in windows]

    return [window for window in parsed if window > 0]


def parse_indicators(indicators: Iterable[str] | str | None) -> list[str]:
    """Normalize technical indicator names from list-like or comma-separated strings."""
    if indicators is None:
        return []

    if isinstance(indicators, str):
        if not indicators.strip():
            return []
        values = indicators.replace("\uFF0C", ",").split(",")
    else:
        values = list(indicators)

    aliases = {
        "bb": "bollinger",
        "boll": "bollinger",
        "bollinger_bands": "bollinger",
    }

    parsed: list[str] = []
    for value in values:
        name = str(value).strip().lower()
        if not name:
            continue
        parsed.append(aliases.get(name, name))

    return list(dict.fromkeys(parsed))


def calc_moving_average(series: pd.Series, window: int) -> pd.Series:
    """Calculate simple moving average."""
    return pd.to_numeric(series, errors="coerce").rolling(window).mean()


def calc_exponential_moving_average(series: pd.Series, span: int) -> pd.Series:
    """Calculate exponential moving average."""
    return pd.to_numeric(series, errors="coerce").ewm(span=span, adjust=False).mean()


def latest_moving_average(series: pd.Series, window: int) -> float | None:
    """Return latest simple moving average when enough observations exist."""
    numeric = pd.to_numeric(series, errors="coerce")

    if len(numeric.dropna()) < window:
        return None

    value = calc_moving_average(numeric, window).iloc[-1]

    if pd.isna(value):
        return None

    return round(float(value), 4)


def calc_bollinger_bands(
    series: pd.Series,
    window: int = 20,
    num_std: float = 2.0,
) -> pd.DataFrame:
    """Calculate Bollinger Bands."""
    numeric = pd.to_numeric(series, errors="coerce")
    middle = numeric.rolling(window).mean()
    std = numeric.rolling(window).std()

    return pd.DataFrame(
        {
            "boll_middle": middle,
            "boll_upper": middle + num_std * std,
            "boll_lower": middle - num_std * std,
        }
    )


def calc_rsi(series: pd.Series, window: int = 14) -> pd.Series:
    """Calculate Relative Strength Index."""
    numeric = pd.to_numeric(series, errors="coerce")
    delta = numeric.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)

    avg_gain = gain.ewm(alpha=1 / window, min_periods=window, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1 / window, min_periods=window, adjust=False).mean()
    rs = avg_gain / avg_loss.mask(avg_loss == 0)

    return 100 - (100 / (1 + rs))


def calc_macd(
    series: pd.Series,
    fast: int = 12,
    slow: int = 26,
    signal: int = 9,
) -> pd.DataFrame:
    """Calculate MACD line, signal line, and histogram."""
    numeric = pd.to_numeric(series, errors="coerce")
    ema_fast = calc_exponential_moving_average(numeric, fast)
    ema_slow = calc_exponential_moving_average(numeric, slow)
    dif = ema_fast - ema_slow
    dea = calc_exponential_moving_average(dif, signal)

    return pd.DataFrame(
        {
            "macd_dif": dif,
            "macd_dea": dea,
            "macd_hist": (dif - dea) * 2,
        }
    )


def calc_kdj(
    high: pd.Series,
    low: pd.Series,
    close: pd.Series,
    window: int = 9,
    k_window: int = 3,
    d_window: int = 3,
) -> pd.DataFrame:
    """Calculate KDJ indicator."""
    high_numeric = pd.to_numeric(high, errors="coerce")
    low_numeric = pd.to_numeric(low, errors="coerce")
    close_numeric = pd.to_numeric(close, errors="coerce")

    low_min = low_numeric.rolling(window).min()
    high_max = high_numeric.rolling(window).max()
    rsv = (close_numeric - low_min) / (high_max - low_min).mask((high_max - low_min) == 0) * 100
    k = rsv.ewm(alpha=1 / k_window, adjust=False).mean()
    d = k.ewm(alpha=1 / d_window, adjust=False).mean()

    return pd.DataFrame(
        {
            "kdj_k": k,
            "kdj_d": d,
            "kdj_j": 3 * k - 2 * d,
        }
    )
