from __future__ import annotations

from dataclasses import replace

from invesagent_core.models.industry import IndustryMember, IndustryMembersResult
from invesagent_core.providers.akshare.industry import (
    get_akshare_industry_members,
    list_akshare_industries,
)
from invesagent_core.providers.tushare.industry import get_cn_industry_members, list_cn_industries
from invesagent_core.services.data.common import DAY_SECONDS, build_quality, cached_result


def _industry_members_from_dict(data: dict) -> IndustryMembersResult:
    return IndustryMembersResult(
        **{
            **data,
            "members": [IndustryMember(**member) for member in data.get("members", [])],
        }
    )


def _with_quality(
    result: IndustryMembersResult,
    *,
    fallback_used: bool = False,
    fallback_from: str | None = None,
) -> IndustryMembersResult:
    quality = build_quality(
        provider=result.provider,
        record_count=len(result.members),
        fallback_used=fallback_used,
        fallback_from=fallback_from,
        data_latency="Industry membership follows provider board/classification refresh timing.",
        missing_fields=[],
    )
    return replace(result, quality=quality)


def list_industries(
    market: str = "cn",
    provider: str = "auto",
) -> dict:
    """List available industries for a market/provider."""
    normalized_market = market.strip().lower()
    normalized_provider = provider.strip().lower()

    def load_uncached() -> dict:
        if normalized_provider == "akshare" and normalized_market == "cn":
            result = list_akshare_industries()
            result["quality"] = build_quality(provider="akshare", record_count=len(result.get("industries", [])))
            return result

        if normalized_provider in ("auto", "tushare") and normalized_market == "cn":
            tushare_result = list_cn_industries()
            if tushare_result.get("success") or normalized_provider == "tushare":
                tushare_result["quality"] = build_quality(
                    provider="tushare",
                    record_count=len(tushare_result.get("industries", [])),
                )
                return tushare_result

            akshare_result = list_akshare_industries()
            if akshare_result.get("success"):
                akshare_result.setdefault("warnings", []).append("Tushare request failed; AKShare fallback was used.")
                akshare_result["quality"] = build_quality(
                    provider="akshare",
                    record_count=len(akshare_result.get("industries", [])),
                    fallback_used=True,
                    fallback_from=f"tushare:{tushare_result.get('error_type') or 'unknown_error'}",
                )
                return akshare_result

            tushare_result.setdefault("warnings", []).append(
                f"AKShare fallback also failed: {akshare_result.get('error_type') or 'unknown_error'}."
            )
            return tushare_result

        return {
            "success": False,
            "provider": normalized_provider,
            "market": normalized_market,
            "error_type": "unsupported_market",
            "message": f"Unsupported industry list provider combination: market={market}, provider={provider}",
            "industries": [],
            "quality": build_quality(provider=normalized_provider, record_count=0),
        }

    return cached_result(
        namespace="industry_list",
        ttl_seconds=DAY_SECONDS,
        loader=load_uncached,
        serializer=lambda result: result,
        deserializer=lambda data: {**data, "quality": {**data.get("quality", {}), "cache_hit": True}},
        cache_parts={"provider": normalized_provider, "market": normalized_market},
    )


def get_industry_members(
    industry: str,
    market: str = "cn",
    provider: str = "auto",
    match_mode: str = "fuzzy",
    limit: int | None = None,
) -> IndustryMembersResult:
    """Fetch industry members through the unified data layer."""
    normalized_market = market.strip().lower()
    normalized_provider = provider.strip().lower()

    def load_uncached() -> IndustryMembersResult:
        if normalized_provider == "akshare" and normalized_market == "cn":
            return _with_quality(get_akshare_industry_members(industry, match_mode=match_mode, limit=limit))

        if normalized_provider in ("auto", "tushare") and normalized_market == "cn":
            tushare_result = get_cn_industry_members(
                industry=industry,
                match_mode=match_mode,
                limit=limit,
            )
            if tushare_result.success or normalized_provider == "tushare":
                return _with_quality(tushare_result)

            akshare_result = get_akshare_industry_members(industry, match_mode=match_mode, limit=limit)
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
            IndustryMembersResult(
                success=False,
                industry=industry,
                provider=normalized_provider,
                market=normalized_market,
                error_type="unsupported_market",
                message=(
                    "Unsupported industry member provider combination: "
                    f"market={market}, provider={provider}"
                ),
            )
        )

    return cached_result(
        namespace="industry_members",
        ttl_seconds=DAY_SECONDS,
        loader=load_uncached,
        serializer=lambda result: result.to_dict(),
        deserializer=_industry_members_from_dict,
        cache_parts={
            "provider": normalized_provider,
            "market": normalized_market,
            "industry": industry,
            "match_mode": match_mode,
            "limit": limit,
        },
    )
