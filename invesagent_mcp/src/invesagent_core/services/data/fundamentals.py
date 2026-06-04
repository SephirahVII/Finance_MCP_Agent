from __future__ import annotations

from dataclasses import replace

from invesagent_core.models.fundamentals import FundamentalRecord, FundamentalsResult
from invesagent_core.providers.akshare.fundamentals import get_akshare_fundamentals
from invesagent_core.providers.tushare.fundamentals import get_cn_fundamentals
from invesagent_core.services.data.common import (
    DAY_SECONDS,
    actual_range_from_records,
    build_quality,
    cached_result,
)
from invesagent_core.utils.dates import normalize_yyyymmdd_date


def _fundamentals_from_dict(data: dict) -> FundamentalsResult:
    return FundamentalsResult(
        **{
            **data,
            "records": [FundamentalRecord(**record) for record in data.get("records", [])],
        }
    )


def _with_quality(
    result: FundamentalsResult,
    *,
    fallback_used: bool = False,
    fallback_from: str | None = None,
) -> FundamentalsResult:
    actual = actual_range_from_records(result.records, "period")
    quality = build_quality(
        provider=result.provider,
        requested_start_date=result.start_date,
        requested_end_date=result.end_date,
        actual_start_date=actual["start_date"],
        actual_end_date=actual["end_date"],
        record_count=len(result.records),
        fallback_used=fallback_used,
        fallback_from=fallback_from,
        data_latency="Financial statement data depends on company disclosure and provider refresh timing.",
        missing_fields=[],
    )
    return replace(result, quality=quality)


def get_fundamentals(
    symbol: str,
    market: str,
    data_type: str,
    start_date: str,
    end_date: str,
    asset_type: str = "stock",
    provider: str = "auto",
) -> FundamentalsResult:
    """Unified fundamentals data service with AKShare fallback and cache."""
    start_date = normalize_yyyymmdd_date(start_date)
    end_date = normalize_yyyymmdd_date(end_date)
    normalized_market = market.strip().lower()
    normalized_asset_type = asset_type.strip().lower()
    normalized_provider = provider.strip().lower()
    normalized_data_type = data_type.strip().lower()

    def load_uncached() -> FundamentalsResult:
        if normalized_provider == "akshare" and normalized_market == "cn" and normalized_asset_type == "stock":
            return _with_quality(
                get_akshare_fundamentals(
                    symbol=symbol,
                    start_date=start_date,
                    end_date=end_date,
                    data_type=normalized_data_type,
                    asset_type=normalized_asset_type,
                )
            )

        if normalized_provider in ("auto", "tushare") and normalized_market == "cn" and normalized_asset_type == "stock":
            tushare_result = get_cn_fundamentals(
                symbol=symbol,
                start_date=start_date,
                end_date=end_date,
                data_type=normalized_data_type,
                asset_type=normalized_asset_type,
            )
            if tushare_result.success or normalized_provider == "tushare":
                return _with_quality(tushare_result)

            akshare_result = get_akshare_fundamentals(
                symbol=symbol,
                start_date=start_date,
                end_date=end_date,
                data_type=normalized_data_type,
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
            FundamentalsResult(
                success=False,
                symbol=symbol,
                start_date=start_date,
                end_date=end_date,
                provider=normalized_provider,
                market=normalized_market,
                asset_type=normalized_asset_type,
                data_type=normalized_data_type,
                error_type="unsupported_market",
                message=(
                    "Unsupported fundamentals provider combination: "
                    f"market={market}, asset_type={asset_type}, provider={provider}"
                ),
            )
        )

    return cached_result(
        namespace="fundamentals",
        ttl_seconds=DAY_SECONDS,
        loader=load_uncached,
        serializer=lambda result: result.to_dict(),
        deserializer=_fundamentals_from_dict,
        cache_parts={
            "provider": normalized_provider,
            "market": normalized_market,
            "asset_type": normalized_asset_type,
            "symbol": symbol,
            "data_type": normalized_data_type,
            "start_date": start_date,
            "end_date": end_date,
        },
    )
