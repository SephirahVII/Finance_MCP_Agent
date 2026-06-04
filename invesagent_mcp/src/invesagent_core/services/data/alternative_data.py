from __future__ import annotations

from dataclasses import replace

from invesagent_core.models.alternative_data import AlternativeDataRecord, AlternativeDataResult
from invesagent_core.providers.akshare.alternative_data import fetch_akshare_alternative_data
from invesagent_core.providers.tushare.alternative_data import fetch_tushare_alternative_data
from invesagent_core.services.data.common import (
    DAY_SECONDS,
    actual_range_from_records,
    build_quality,
    cached_result,
)
from invesagent_core.utils.dates import normalize_yyyymmdd_date


CATEGORIES = {
    "announcements",
    "financial_disclosure_dates",
    "dividends",
    "shareholder_counts",
    "top_shareholders",
    "float_top_shareholders",
    "northbound_capital",
    "money_flow",
    "dragon_tiger",
    "block_trades",
    "index_weights",
    "sector_quotes",
    "news",
    "research_reports",
    "macro",
}


def _result_from_dict(data: dict) -> AlternativeDataResult:
    return AlternativeDataResult(
        **{
            **data,
            "records": [AlternativeDataRecord(**record) for record in data.get("records", [])],
        }
    )


def _with_quality(
    result: AlternativeDataResult,
    *,
    fallback_used: bool = False,
    fallback_from: str | None = None,
) -> AlternativeDataResult:
    actual = actual_range_from_records(result.records, "date")
    quality = build_quality(
        provider=result.provider,
        requested_start_date=result.start_date,
        requested_end_date=result.end_date,
        actual_start_date=actual["start_date"],
        actual_end_date=actual["end_date"],
        record_count=len(result.records),
        fallback_used=fallback_used,
        fallback_from=fallback_from,
        data_latency="Depends on provider source and data category refresh cadence.",
        missing_fields=[],
        notes=[f"category={result.category}"],
    )
    return replace(result, quality=quality)


def get_alternative_data(
    *,
    category: str,
    market: str = "cn",
    symbol: str | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
    provider: str = "auto",
    keyword: str | None = None,
    limit: int = 50,
) -> AlternativeDataResult:
    """Unified data service for non-core financial datasets."""
    normalized_category = category.strip().lower()
    normalized_market = market.strip().lower()
    normalized_provider = provider.strip().lower()
    normalized_start = normalize_yyyymmdd_date(start_date or "") or None
    normalized_end = normalize_yyyymmdd_date(end_date or "") or None

    def unsupported() -> AlternativeDataResult:
        return _with_quality(
            AlternativeDataResult(
                success=False,
                category=normalized_category,
                provider=normalized_provider,
                market=normalized_market,
                symbol=symbol,
                start_date=normalized_start,
                end_date=normalized_end,
                error_type="unsupported_category",
                message=f"Unsupported alternative data category: {category}",
            )
        )

    def load_uncached() -> AlternativeDataResult:
        if normalized_category not in CATEGORIES:
            return unsupported()

        if normalized_provider == "tushare":
            return _with_quality(
                fetch_tushare_alternative_data(
                    category=normalized_category,
                    market=normalized_market,
                    symbol=symbol,
                    start_date=normalized_start,
                    end_date=normalized_end,
                    keyword=keyword,
                    limit=limit,
                )
            )

        if normalized_provider == "akshare":
            return _with_quality(
                fetch_akshare_alternative_data(
                    category=normalized_category,
                    market=normalized_market,
                    symbol=symbol,
                    start_date=normalized_start,
                    end_date=normalized_end,
                    keyword=keyword,
                    limit=limit,
                )
            )

        if normalized_provider == "auto":
            tushare_result = fetch_tushare_alternative_data(
                category=normalized_category,
                market=normalized_market,
                symbol=symbol,
                start_date=normalized_start,
                end_date=normalized_end,
                keyword=keyword,
                limit=limit,
            )
            if tushare_result.success:
                return _with_quality(tushare_result)

            akshare_result = fetch_akshare_alternative_data(
                category=normalized_category,
                market=normalized_market,
                symbol=symbol,
                start_date=normalized_start,
                end_date=normalized_end,
                keyword=keyword,
                limit=limit,
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
            AlternativeDataResult(
                success=False,
                category=normalized_category,
                provider=normalized_provider,
                market=normalized_market,
                symbol=symbol,
                start_date=normalized_start,
                end_date=normalized_end,
                error_type="unsupported_provider",
                message=f"Unsupported provider: {provider}",
            )
        )

    return cached_result(
        namespace="alternative_data",
        ttl_seconds=DAY_SECONDS,
        loader=load_uncached,
        serializer=lambda result: result.to_dict(),
        deserializer=_result_from_dict,
        cache_parts={
            "category": normalized_category,
            "provider": normalized_provider,
            "market": normalized_market,
            "symbol": symbol,
            "start_date": normalized_start,
            "end_date": normalized_end,
            "keyword": keyword,
            "limit": limit,
        },
    )
