from __future__ import annotations

from dataclasses import replace

from invesagent_core.models.market_data import MarketDataResult, OHLCVRecord
from invesagent_core.providers.akshare.market_data import get_akshare_ohlcv
from invesagent_core.providers.tushare.market_data import get_cn_ohlcv, get_trade_calendar
from invesagent_core.services.data.common import (
    DAY_SECONDS,
    actual_range_from_records,
    build_quality,
    cached_result,
    missing_fields_from_records,
)
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


def _market_data_from_dict(data: dict) -> MarketDataResult:
    return MarketDataResult(
        **{
            **data,
            "records": [OHLCVRecord(**record) for record in data.get("records", [])],
        }
    )


def _with_market_quality(
    result: MarketDataResult,
    *,
    fallback_used: bool = False,
    fallback_from: str | None = None,
) -> MarketDataResult:
    actual = actual_range_from_records(result.records, "trade_time")
    quality = build_quality(
        provider=result.provider,
        requested_start_date=result.start_date,
        requested_end_date=result.end_date,
        actual_start_date=actual["start_date"],
        actual_end_date=actual["end_date"],
        record_count=len(result.records),
        fallback_used=fallback_used,
        fallback_from=fallback_from,
        data_latency="T+1 for daily bars when provider data is updated after market close.",
        missing_fields=missing_fields_from_records(
            result.records,
            ["open", "high", "low", "close", "volume", "amount"],
        ),
    )
    return replace(result, quality=quality)


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
    """Unified OHLCV data service with provider fallback and local cache."""
    start_date = normalize_yyyymmdd_date(start_date)
    end_date = normalize_yyyymmdd_date(end_date)
    normalized_market = market.strip().lower()
    normalized_asset_type = asset_type.strip().lower()
    normalized_provider = provider.strip().lower()

    def load_uncached() -> MarketDataResult:
        if normalized_provider == "akshare" and _akshare_supported(
            normalized_market,
            normalized_asset_type,
        ):
            return _with_market_quality(
                get_akshare_ohlcv(
                    symbol=symbol,
                    market=normalized_market,
                    asset_type=normalized_asset_type,
                    start_date=start_date,
                    end_date=end_date,
                    frequency=frequency,
                    adjust=adjust,
                )
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
                return _with_market_quality(tushare_result)

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
                    akshare_result.warnings.append("Tushare request failed; AKShare fallback was used.")
                    return _with_market_quality(
                        akshare_result,
                        fallback_used=True,
                        fallback_from=f"tushare:{tushare_result.error_type or 'unknown_error'}",
                    )

                tushare_result.warnings.append(
                    f"AKShare fallback also failed: {akshare_result.error_type or 'unknown_error'}."
                )
                return _with_market_quality(tushare_result)

        if normalized_provider == "auto" and _akshare_supported(
            normalized_market,
            normalized_asset_type,
        ):
            return _with_market_quality(
                get_akshare_ohlcv(
                    symbol=symbol,
                    market=normalized_market,
                    asset_type=normalized_asset_type,
                    start_date=start_date,
                    end_date=end_date,
                    frequency=frequency,
                    adjust=adjust,
                )
            )

        return _with_market_quality(
            MarketDataResult(
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
        )

    return cached_result(
        namespace="ohlcv",
        ttl_seconds=DAY_SECONDS,
        loader=load_uncached,
        serializer=lambda result: result.to_dict(),
        deserializer=_market_data_from_dict,
        cache_parts={
            "provider": normalized_provider,
            "market": normalized_market,
            "asset_type": normalized_asset_type,
            "symbol": symbol,
            "start_date": start_date,
            "end_date": end_date,
            "frequency": frequency,
            "adjust": adjust,
        },
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
