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

        values = windows.replace("，", ",").split(",")
        parsed = [int(value.strip()) for value in values if value.strip()]
    else:
        parsed = [int(value) for value in windows]

    return [window for window in parsed if window > 0]


def calc_moving_average(series: pd.Series, window: int) -> pd.Series:
    """Calculate simple moving average."""
    return pd.to_numeric(series, errors="coerce").rolling(window).mean()


def latest_moving_average(series: pd.Series, window: int) -> float | None:
    """Return latest simple moving average when enough observations exist."""
    numeric = pd.to_numeric(series, errors="coerce")

    if len(numeric.dropna()) < window:
        return None

    value = calc_moving_average(numeric, window).iloc[-1]

    if pd.isna(value):
        return None

    return round(float(value), 4)
