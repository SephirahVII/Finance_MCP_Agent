from __future__ import annotations

import pandas as pd

from invesagent_core.models.market_data import MarketDataResult, OHLCVRecord
from invesagent_core.providers.akshare.client import get_client
from invesagent_core.providers.akshare.instruments import (
    normalize_cn_symbol,
    normalize_hk_symbol,
    normalize_us_symbol,
)


DATE_COLUMNS = ["date", "\u65e5\u671f", "\u65f6\u95f4"]
OPEN_COLUMNS = ["open", "\u5f00\u76d8", "\u5f00\u76d8\u4ef7"]
HIGH_COLUMNS = ["high", "\u6700\u9ad8", "\u6700\u9ad8\u4ef7"]
LOW_COLUMNS = ["low", "\u6700\u4f4e", "\u6700\u4f4e\u4ef7"]
CLOSE_COLUMNS = ["close", "\u6536\u76d8", "\u6536\u76d8\u4ef7"]
VOLUME_COLUMNS = ["volume", "\u6210\u4ea4\u91cf", "\u6210\u4ea4\u91cf(\u80a1)"]
AMOUNT_COLUMNS = ["amount", "\u6210\u4ea4\u989d", "\u6210\u4ea4\u989d(\u5143)"]


def _classify_akshare_error(error: Exception, api_name: str) -> tuple[str, str]:
    raw_error = str(error)

    if "not installed" in raw_error:
        return "dependency_missing", raw_error

    if "timeout" in raw_error.lower() or "timed out" in raw_error.lower():
        return "network_timeout", f"AKShare {api_name} request timed out."

    return "akshare_error", f"Failed to fetch AKShare {api_name} data."


def _to_float(value) -> float | None:
    if value is None or value == "":
        return None

    try:
        converted = float(value)
    except (TypeError, ValueError):
        return None

    if pd.isna(converted):
        return None

    return converted


def _normalize_date_value(value) -> str:
    if value is None or value == "":
        return ""

    try:
        parsed = pd.to_datetime(value)
    except Exception:
        return str(value).replace("-", "")[:8]

    if pd.isna(parsed):
        return str(value)

    return parsed.strftime("%Y%m%d")


def _pick(item: dict, names: list[str]):
    for name in names:
        if name in item:
            return item.get(name)
    return None


def _ensure_date_column(df: pd.DataFrame) -> pd.DataFrame:
    working = df.copy()

    if working.index.name and working.index.name.lower() in ("date", "\u65e5\u671f"):
        return working.reset_index()

    if not any(column in working.columns for column in DATE_COLUMNS) and not isinstance(
        working.index,
        pd.RangeIndex,
    ):
        return working.reset_index().rename(columns={"index": "date"})

    return working


def _akshare_ohlcv_to_records(
    df: pd.DataFrame,
    symbol: str,
    market: str,
    asset_type: str,
) -> list[OHLCVRecord]:
    """Convert common AKShare OHLCV DataFrames to unified records."""
    if df is None or df.empty:
        return []

    working = _ensure_date_column(df)
    records: list[OHLCVRecord] = []

    for item in working.fillna("").to_dict(orient="records"):
        open_price = _to_float(_pick(item, OPEN_COLUMNS))
        high_price = _to_float(_pick(item, HIGH_COLUMNS))
        low_price = _to_float(_pick(item, LOW_COLUMNS))
        close_price = _to_float(_pick(item, CLOSE_COLUMNS))

        if None in (open_price, high_price, low_price, close_price):
            continue

        records.append(
            OHLCVRecord(
                symbol=symbol,
                trade_time=_normalize_date_value(_pick(item, DATE_COLUMNS)),
                open=open_price,
                high=high_price,
                low=low_price,
                close=close_price,
                volume=_to_float(_pick(item, VOLUME_COLUMNS)),
                amount=_to_float(_pick(item, AMOUNT_COLUMNS)),
                provider="akshare",
                market=market,
                asset_type=asset_type,
                raw=item,
            )
        )

    return sorted(records, key=lambda record: record.trade_time)


def _build_market_result(
    success: bool,
    symbol: str,
    market: str,
    asset_type: str,
    start_date: str,
    end_date: str,
    records: list[OHLCVRecord] | None = None,
    error_type: str | None = None,
    message: str | None = None,
    raw: dict | None = None,
) -> MarketDataResult:
    return MarketDataResult(
        success=success,
        symbol=symbol,
        start_date=start_date,
        end_date=end_date,
        provider="akshare",
        market=market,
        asset_type=asset_type,
        records=records or [],
        error_type=error_type,
        message=message,
        raw=raw,
    )


def _normalize_akshare_period(frequency: str) -> str:
    normalized = frequency.strip().lower()

    if normalized in ("daily", "d", "1d"):
        return "daily"
    if normalized in ("weekly", "w", "1w"):
        return "weekly"
    if normalized in ("monthly", "m", "1m"):
        return "monthly"

    return normalized


def _normalize_cn_index_symbol(symbol: str) -> str:
    value = symbol.strip().lower()

    if "." in value:
        code, exchange = value.split(".", 1)
        if exchange == "sh":
            return f"sh{code}"
        if exchange == "sz":
            return f"sz{code}"

    if value.startswith(("sh", "sz")):
        return value

    if value.startswith(("000", "930", "931")):
        return f"sh{value}"

    if value.startswith(("399", "980")):
        return f"sz{value}"

    return value


def _normalize_adjust(adjust: str | None) -> str:
    if not adjust:
        return ""

    normalized = adjust.strip().lower()

    if normalized in ("none", "no", "unadjusted"):
        return ""

    return normalized


def _fetch_cn_etf_or_fund(
    ak,
    symbol: str,
    period: str,
    start_date: str,
    end_date: str,
    adjust: str,
) -> pd.DataFrame:
    """Fetch China ETF/fund OHLCV from AKShare Eastmoney fund adapter."""
    try:
        return ak.fund_etf_hist_em(
            symbol=normalize_cn_symbol(symbol),
            period=period,
            start_date=start_date,
            end_date=end_date,
            adjust=adjust,
        )
    except TypeError:
        return ak.fund_etf_hist_em(
            symbol=normalize_cn_symbol(symbol),
            period=period,
            start_date=start_date,
            end_date=end_date,
        )


def _fetch_us_hist(
    ak,
    symbol: str,
    period: str,
    start_date: str,
    end_date: str,
    adjust: str,
) -> tuple[str, pd.DataFrame]:
    """Fetch US OHLCV with a fallback for AKShare versions with different APIs."""
    normalized_symbol = normalize_us_symbol(symbol)

    try:
        return (
            "stock_us_hist",
            ak.stock_us_hist(
                symbol=normalized_symbol,
                period=period,
                start_date=start_date,
                end_date=end_date,
                adjust=adjust,
            ),
        )
    except Exception:
        df = ak.stock_us_daily(
            symbol=normalized_symbol.split(".")[-1],
            adjust=adjust,
        )
        return "stock_us_daily", _filter_by_date(df, start_date=start_date, end_date=end_date)


def get_akshare_ohlcv(
    symbol: str,
    market: str,
    asset_type: str,
    start_date: str,
    end_date: str,
    frequency: str = "daily",
    adjust: str | None = None,
) -> MarketDataResult:
    """Fetch OHLCV data from AKShare for CN/HK/US stocks, ETFs, funds, and indexes."""
    normalized_market = market.strip().lower()
    normalized_asset_type = asset_type.strip().lower()
    period = _normalize_akshare_period(frequency)
    normalized_adjust = _normalize_adjust(adjust)

    if period not in ("daily", "weekly", "monthly"):
        return _build_market_result(
            success=False,
            symbol=symbol,
            market=normalized_market,
            asset_type=normalized_asset_type,
            start_date=start_date,
            end_date=end_date,
            error_type="unsupported_frequency",
            message="AKShare OHLCV currently supports daily, weekly, and monthly frequency.",
        )

    try:
        ak = get_client()

        if normalized_market == "cn":
            if normalized_asset_type == "index":
                api_name = "stock_zh_index_daily"
                try:
                    df = ak.stock_zh_index_daily(
                        symbol=_normalize_cn_index_symbol(symbol),
                        start_date=start_date,
                        end_date=end_date,
                    )
                except TypeError:
                    df = ak.stock_zh_index_daily(symbol=_normalize_cn_index_symbol(symbol))
                    df = _filter_by_date(df, start_date=start_date, end_date=end_date)
            elif normalized_asset_type in ("etf", "fund"):
                api_name = "fund_etf_hist_em"
                df = _fetch_cn_etf_or_fund(
                    ak=ak,
                    symbol=symbol,
                    period=period,
                    start_date=start_date,
                    end_date=end_date,
                    adjust=normalized_adjust,
                )
            else:
                api_name = "stock_zh_a_hist"
                df = ak.stock_zh_a_hist(
                    symbol=normalize_cn_symbol(symbol),
                    period=period,
                    start_date=start_date,
                    end_date=end_date,
                    adjust=normalized_adjust,
                )
        elif normalized_market == "hk":
            api_name = "stock_hk_hist"
            df = ak.stock_hk_hist(
                symbol=normalize_hk_symbol(symbol),
                period=period,
                start_date=start_date,
                end_date=end_date,
                adjust=normalized_adjust,
            )
        elif normalized_market == "us":
            api_name, df = _fetch_us_hist(
                ak=ak,
                symbol=symbol,
                period=period,
                start_date=start_date,
                end_date=end_date,
                adjust=normalized_adjust,
            )
        else:
            return _build_market_result(
                success=False,
                symbol=symbol,
                market=normalized_market,
                asset_type=normalized_asset_type,
                start_date=start_date,
                end_date=end_date,
                error_type="unsupported_market",
                message=f"AKShare OHLCV does not support market={market} yet.",
            )
    except Exception as exc:
        error_type, message = _classify_akshare_error(exc, locals().get("api_name", "ohlcv"))
        return _build_market_result(
            success=False,
            symbol=symbol,
            market=normalized_market,
            asset_type=normalized_asset_type,
            start_date=start_date,
            end_date=end_date,
            error_type=error_type,
            message=message,
            raw={"raw_error": str(exc)},
        )

    records = _akshare_ohlcv_to_records(
        df=df,
        symbol=symbol,
        market=normalized_market,
        asset_type=normalized_asset_type,
    )

    if not records:
        return _build_market_result(
            success=False,
            symbol=symbol,
            market=normalized_market,
            asset_type=normalized_asset_type,
            start_date=start_date,
            end_date=end_date,
            error_type="empty_data",
            message=f"No AKShare {api_name} data returned.",
        )

    return _build_market_result(
        success=True,
        symbol=symbol,
        market=normalized_market,
        asset_type=normalized_asset_type,
        start_date=start_date,
        end_date=end_date,
        records=records,
    )


def _filter_by_date(
    df: pd.DataFrame,
    start_date: str,
    end_date: str,
) -> pd.DataFrame:
    """Filter AKShare output by date when the underlying API has no date arguments."""
    if df is None or df.empty:
        return df

    working = _ensure_date_column(df)
    date_column = next((column for column in DATE_COLUMNS if column in working.columns), None)

    if date_column is None:
        return working

    dates = pd.to_datetime(working[date_column], errors="coerce")
    start = pd.to_datetime(start_date, format="%Y%m%d", errors="coerce")
    end = pd.to_datetime(end_date, format="%Y%m%d", errors="coerce")

    if not pd.isna(start):
        working = working.loc[dates >= start]

    dates = pd.to_datetime(working[date_column], errors="coerce")
    if not pd.isna(end):
        working = working.loc[dates <= end]

    return working
