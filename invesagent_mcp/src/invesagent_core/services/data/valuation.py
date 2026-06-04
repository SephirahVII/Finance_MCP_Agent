from __future__ import annotations

from dataclasses import replace

from invesagent_core.models.valuation import ValuationRecord, ValuationResult
from invesagent_core.providers.akshare.valuation import get_akshare_valuation
from invesagent_core.providers.tushare.valuation import get_cn_daily_basic
from invesagent_core.services.data.common import (
    DAY_SECONDS,
    actual_range_from_records,
    build_quality,
    cached_result,
    missing_fields_from_records,
)
from invesagent_core.utils.dates import normalize_yyyymmdd_date


def _valuation_from_dict(data: dict) -> ValuationResult:
    return ValuationResult(
        **{
            **data,
            "records": [ValuationRecord(**record) for record in data.get("records", [])],
        }
    )


def _with_quality(
    result: ValuationResult,
    *,
    fallback_used: bool = False,
    fallback_from: str | None = None,
) -> ValuationResult:
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
        data_latency="T+1 where valuation metrics are sourced from daily market data.",
        missing_fields=missing_fields_from_records(
            result.records,
            ["pe_ttm", "pb", "ps_ttm", "total_mv", "circ_mv", "turnover_rate"],
        ),
    )
    return replace(result, quality=quality)


def get_valuation(
    symbol: str,
    market: str,
    asset_type: str = "stock",
    start_date: str = "",
    end_date: str = "",
    provider: str = "auto",
) -> ValuationResult:
    """Unified valuation data service with AKShare fallback and cache."""
    start_date = normalize_yyyymmdd_date(start_date)
    end_date = normalize_yyyymmdd_date(end_date)
    normalized_market = market.strip().lower()
    normalized_asset_type = asset_type.strip().lower()
    normalized_provider = provider.strip().lower()

    def load_uncached() -> ValuationResult:
        if normalized_provider == "akshare" and normalized_market == "cn" and normalized_asset_type == "stock":
            return _with_quality(
                get_akshare_valuation(
                    symbol=symbol,
                    start_date=start_date,
                    end_date=end_date,
                    asset_type=normalized_asset_type,
                )
            )

        if normalized_provider in ("auto", "tushare") and normalized_market == "cn" and normalized_asset_type in (
            "stock",
            "etf",
        ):
            tushare_result = get_cn_daily_basic(
                symbol=symbol,
                start_date=start_date,
                end_date=end_date,
                asset_type=normalized_asset_type,
            )
            if tushare_result.success or normalized_provider == "tushare" or normalized_asset_type != "stock":
                return _with_quality(tushare_result)

            akshare_result = get_akshare_valuation(
                symbol=symbol,
                start_date=start_date,
                end_date=end_date,
                asset_type=normalized_asset_type,
            )
            if akshare_result.success:
                akshare_result.warnings.append("Tushare request failed; AKShare fallback was used.")
                return _with_quality(
                    akshare_result,
                    fallback_used=True,
                    fallback_from=f"tushare:{tushare_result.error_type or 'unknown_error'}",
                )

            tushare_result.warnings.append(
                f"AKShare fallback also failed: {akshare_result.error_type or 'unknown_error'}."
            )
            return _with_quality(tushare_result)

        return _with_quality(
            ValuationResult(
                success=False,
                symbol=symbol,
                start_date=start_date,
                end_date=end_date,
                provider=normalized_provider,
                market=normalized_market,
                asset_type=normalized_asset_type,
                error_type="unsupported_market",
                message=(
                    "Unsupported valuation provider combination: "
                    f"market={market}, asset_type={asset_type}, provider={provider}"
                ),
            )
        )

    return cached_result(
        namespace="valuation",
        ttl_seconds=DAY_SECONDS,
        loader=load_uncached,
        serializer=lambda result: result.to_dict(),
        deserializer=_valuation_from_dict,
        cache_parts={
            "provider": normalized_provider,
            "market": normalized_market,
            "asset_type": normalized_asset_type,
            "symbol": symbol,
            "start_date": start_date,
            "end_date": end_date,
        },
    )
