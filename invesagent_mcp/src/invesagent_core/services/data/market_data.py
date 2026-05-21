from __future__ import annotations

from invesagent_core.models.market_data import MarketDataResult
from invesagent_core.providers.akshare.market_data import get_akshare_ohlcv
from invesagent_core.providers.tushare.market_data import get_cn_ohlcv, get_trade_calendar
from invesagent_core.utils.dates import normalize_yyyymmdd_date


def _akshare_supported(market: str, asset_type: str) -> bool:
    normalized_market = market.strip().lower()
    normalized_asset_type = asset_type.strip().lower()

    return normalized_market in ("cn", "hk", "us") and normalized_asset_type in (
        "stock",
        "index",
        "etf",
        "fund",
    )


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
    normalized_market = market.strip().lower()
    normalized_asset_type = asset_type.strip().lower()
    normalized_provider = provider.strip().lower()

    if normalized_provider == "akshare" and _akshare_supported(
        normalized_market,
        normalized_asset_type,
    ):
        return get_akshare_ohlcv(
            symbol=symbol,
            market=normalized_market,
            asset_type=normalized_asset_type,
            start_date=start_date,
            end_date=end_date,
            frequency=frequency,
            adjust=adjust,
        )

    if normalized_provider in ("auto", "tushare") and normalized_market == "cn" and normalized_asset_type in (
        "stock",
        "index",
    ):
        tushare_result = get_cn_ohlcv(
            symbol=symbol,
            start_date=start_date,
            end_date=end_date,
            asset_type=normalized_asset_type,
            frequency=frequency,
            adjust=adjust,
        )

        if tushare_result.success or normalized_provider == "tushare":
            return tushare_result

        if _akshare_supported(normalized_market, normalized_asset_type):
            akshare_result = get_akshare_ohlcv(
                symbol=symbol,
                market=normalized_market,
                asset_type=normalized_asset_type,
                start_date=start_date,
                end_date=end_date,
                frequency=frequency,
                adjust=adjust,
            )

            if akshare_result.success:
                akshare_result.warnings.append(
                    "Tushare request failed; AKShare fallback was used."
                )
                return akshare_result

            tushare_result.warnings.append(
                f"AKShare fallback also failed: {akshare_result.error_type or 'unknown_error'}."
            )
            return tushare_result

    if normalized_provider == "auto" and _akshare_supported(
        normalized_market,
        normalized_asset_type,
    ):
        return get_akshare_ohlcv(
            symbol=symbol,
            market=normalized_market,
            asset_type=normalized_asset_type,
            start_date=start_date,
            end_date=end_date,
            frequency=frequency,
            adjust=adjust,
        )

    return MarketDataResult(
        success=False,
        symbol=symbol,
        start_date=start_date,
        end_date=end_date,
        provider=normalized_provider,
        market=normalized_market,
        asset_type=normalized_asset_type,
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
