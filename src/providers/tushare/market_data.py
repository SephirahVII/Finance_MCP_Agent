from __future__ import annotations

import pandas as pd

from src.models.market_data import MarketDataResult, OHLCVRecord
from src.providers.tushare.client import get_client
from src.config.settings import settings


def _classify_tushare_error(error: Exception, api_name: str) -> tuple[str, str]:
    raw_error = str(error)

    if "没有接口" in raw_error or "权限" in raw_error:
        return "permission_denied", f"Current Tushare token does not have {api_name} access."

    if "频率" in raw_error or "超限" in raw_error:
        return "rate_limited", f"Tushare {api_name} request is rate limited."

    return "tushare_error", f"Failed to fetch Tushare {api_name} data."


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


def _tushare_ohlcv_to_records(
    df: pd.DataFrame,
    symbol: str,
    market: str,
    asset_type: str,
) -> list[OHLCVRecord]:
    """Convert a Tushare OHLCV-like DataFrame to unified records."""
    if df is None or df.empty:
        return []

    df = df.sort_values("trade_date").fillna("")

    records: list[OHLCVRecord] = []

    for item in df.to_dict(orient="records"):
        records.append(
            OHLCVRecord(
                symbol=symbol,
                trade_time=str(item.get("trade_date")),
                open=float(item.get("open")),
                high=float(item.get("high")),
                low=float(item.get("low")),
                close=float(item.get("close")),
                volume=_to_float(item.get("vol")),
                amount=_to_float(item.get("amount")),
                provider="tushare",
                market=market,
                asset_type=asset_type,
                raw=item,
            )
        )

    return records


def _build_market_result(
    success: bool,
    symbol: str,
    start_date: str,
    end_date: str,
    asset_type: str,
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
        provider="tushare",
        market="cn",
        asset_type=asset_type,
        records=records or [],
        error_type=error_type,
        message=message,
        raw=raw,
    )


def get_cn_ohlcv(
    symbol: str,
    start_date: str,
    end_date: str,
    asset_type: str = "stock",
    frequency: str = "daily",
    adjust: str | None = None,
) -> MarketDataResult:
    """Fetch China-market OHLCV data from Tushare."""
    pro = get_client()
    normalized_frequency = frequency.strip().lower()
    normalized_adjust = adjust.strip().lower() if adjust else None

    api_name = "daily"

    try:
        if normalized_adjust:
            api_name = "pro_bar"
            try:
                import tushare as ts
            except ModuleNotFoundError as exc:
                raise RuntimeError(
                    "The 'tushare' package is not installed. Install it with: pip install tushare"
                ) from exc

            df = ts.pro_bar(
                ts_code=symbol,
                start_date=start_date,
                end_date=end_date,
                adj=normalized_adjust,
                freq={"daily": "D", "weekly": "W", "monthly": "M"}.get(
                    normalized_frequency,
                    normalized_frequency,
                ),
                token=settings.tushare_token,
            )
        elif asset_type == "index":
            if normalized_frequency != "daily":
                return _build_market_result(
                    success=False,
                    symbol=symbol,
                    start_date=start_date,
                    end_date=end_date,
                    asset_type=asset_type,
                    error_type="unsupported_frequency",
                    message="Tushare index OHLCV currently supports daily frequency only.",
                )

            api_name = "index_daily"
            df = pro.index_daily(
                ts_code=symbol,
                start_date=start_date,
                end_date=end_date,
            )
        elif normalized_frequency == "daily":
            api_name = "daily"
            df = pro.daily(
                ts_code=symbol,
                start_date=start_date,
                end_date=end_date,
            )
        elif normalized_frequency == "weekly":
            api_name = "weekly"
            df = pro.weekly(
                ts_code=symbol,
                start_date=start_date,
                end_date=end_date,
            )
        elif normalized_frequency == "monthly":
            api_name = "monthly"
            df = pro.monthly(
                ts_code=symbol,
                start_date=start_date,
                end_date=end_date,
            )
        else:
            return _build_market_result(
                success=False,
                symbol=symbol,
                start_date=start_date,
                end_date=end_date,
                asset_type=asset_type,
                error_type="unsupported_frequency",
                message="frequency must be one of daily, weekly, or monthly.",
            )
    except Exception as exc:
        error_type, message = _classify_tushare_error(exc, api_name)
        return _build_market_result(
            success=False,
            symbol=symbol,
            start_date=start_date,
            end_date=end_date,
            asset_type=asset_type,
            error_type=error_type,
            message=message,
            raw={"raw_error": str(exc)},
        )

    records = _tushare_ohlcv_to_records(
        df=df,
        symbol=symbol,
        market="cn",
        asset_type=asset_type,
    )

    if not records:
        return _build_market_result(
            success=False,
            symbol=symbol,
            start_date=start_date,
            end_date=end_date,
            asset_type=asset_type,
            error_type="empty_data",
            message=f"No Tushare {api_name} data returned.",
        )

    return _build_market_result(
        success=True,
        symbol=symbol,
        start_date=start_date,
        end_date=end_date,
        asset_type=asset_type,
        records=records,
    )


def get_cn_stock_daily(
    symbol: str,
    start_date: str,
    end_date: str,
) -> MarketDataResult:
    """Backward-compatible wrapper for China A-share daily data."""
    return get_cn_ohlcv(
        symbol=symbol,
        start_date=start_date,
        end_date=end_date,
        asset_type="stock",
        frequency="daily",
    )


def get_trade_calendar(
    exchange: str = "SSE",
    start_date: str = "",
    end_date: str = "",
    is_open: str | None = None,
) -> dict:
    """Fetch Tushare trade calendar records."""
    pro = get_client()

    try:
        df = pro.trade_cal(
            exchange=exchange,
            start_date=start_date,
            end_date=end_date,
            is_open=is_open,
        )
    except Exception as exc:
        error_type, message = _classify_tushare_error(exc, "trade_cal")
        return {
            "success": False,
            "provider": "tushare",
            "market": "cn",
            "exchange": exchange,
            "start_date": start_date,
            "end_date": end_date,
            "error_type": error_type,
            "message": message,
            "raw": {"raw_error": str(exc)},
            "records": [],
        }

    if df is None or df.empty:
        return {
            "success": False,
            "provider": "tushare",
            "market": "cn",
            "exchange": exchange,
            "start_date": start_date,
            "end_date": end_date,
            "error_type": "empty_data",
            "message": "No Tushare trade calendar data returned.",
            "records": [],
        }

    return {
        "success": True,
        "provider": "tushare",
        "market": "cn",
        "exchange": exchange,
        "start_date": start_date,
        "end_date": end_date,
        "count": len(df),
        "records": df.fillna("").to_dict(orient="records"),
    }
