from __future__ import annotations

from src.models.market_data import MarketDataResult
from src.providers.tushare.market_data import get_cn_ohlcv, get_trade_calendar
from src.utils.dates import normalize_yyyymmdd_date


def get_ohlcv(
    symbol: str,
    market: str,
    asset_type: str = "stock",
    start_date: str = "",
    end_date: str = "",
    provider: str = "auto",
    frequency: str = "daily",
    adjust: str | None = None,
) -> MarketDataResult:
    """Unified OHLCV data service."""
    start_date = normalize_yyyymmdd_date(start_date)
    end_date = normalize_yyyymmdd_date(end_date)

    if provider in ("auto", "tushare") and market == "cn" and asset_type in ("stock", "index"):
        return get_cn_ohlcv(
            symbol=symbol,
            start_date=start_date,
            end_date=end_date,
            asset_type=asset_type,
            frequency=frequency,
            adjust=adjust,
        )

    return MarketDataResult(
        success=False,
        symbol=symbol,
        start_date=start_date,
        end_date=end_date,
        provider=provider,
        market=market,
        asset_type=asset_type,
        error_type="unsupported_market",
        message=(
            "Unsupported market/provider combination: "
            f"market={market}, asset_type={asset_type}, provider={provider}"
        ),
    )


def get_cn_trade_calendar(
    start_date: str,
    end_date: str,
    exchange: str = "SSE",
    is_open: str | None = None,
    provider: str = "auto",
) -> dict:
    """Unified China-market trade-calendar service."""
    start_date = normalize_yyyymmdd_date(start_date)
    end_date = normalize_yyyymmdd_date(end_date)

    if provider in ("auto", "tushare"):
        return get_trade_calendar(
            exchange=exchange,
            start_date=start_date,
            end_date=end_date,
            is_open=is_open,
        )

    return {
        "success": False,
        "provider": provider,
        "market": "cn",
        "exchange": exchange,
        "start_date": start_date,
        "end_date": end_date,
        "error_type": "unsupported_provider",
        "message": f"Unsupported trade calendar provider: {provider}",
        "records": [],
    }
