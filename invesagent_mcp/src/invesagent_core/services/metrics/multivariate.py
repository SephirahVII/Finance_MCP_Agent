from __future__ import annotations

import pandas as pd

from invesagent_core.services.metrics.price import safe_round


def align_returns_by_time(
    left: pd.DataFrame,
    right: pd.DataFrame,
    time_column: str = "trade_time",
    left_return_column: str = "primary_return",
    right_return_column: str = "benchmark_return",
) -> pd.DataFrame:
    """Align two return series by time and drop rows with missing returns."""
    return pd.merge(left, right, on=time_column, how="inner").dropna(
        subset=[left_return_column, right_return_column]
    )


def calc_correlation(left: pd.Series, right: pd.Series) -> float | None:
    """Calculate correlation between two aligned numeric series."""
    aligned = pd.concat(
        [
            pd.to_numeric(left, errors="coerce"),
            pd.to_numeric(right, errors="coerce"),
        ],
        axis=1,
    ).dropna()

    if len(aligned) < 2:
        return None

    return safe_round(float(aligned.iloc[:, 0].corr(aligned.iloc[:, 1])))


def calc_covariance(left: pd.Series, right: pd.Series) -> float | None:
    """Calculate covariance between two aligned numeric series."""
    aligned = pd.concat(
        [
            pd.to_numeric(left, errors="coerce"),
            pd.to_numeric(right, errors="coerce"),
        ],
        axis=1,
    ).dropna()

    if len(aligned) < 2:
        return None

    return safe_round(float(aligned.iloc[:, 0].cov(aligned.iloc[:, 1])))


def calc_excess_return_pct(
    primary_return_pct: float | None,
    benchmark_return_pct: float | None,
) -> float | None:
    """Calculate primary minus benchmark return."""
    if primary_return_pct is None or benchmark_return_pct is None:
        return None

    return safe_round(primary_return_pct - benchmark_return_pct)


def calc_difference(left: float | None, right: float | None) -> float | None:
    """Calculate left minus right for comparable scalar metrics."""
    if left is None or right is None:
        return None

    return safe_round(left - right)
