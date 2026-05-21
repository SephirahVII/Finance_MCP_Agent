from __future__ import annotations

from invesagent_core.models.industry import IndustryMembersResult
from invesagent_core.providers.tushare.industry import get_cn_industry_members, list_cn_industries


def list_industries(
    market: str = "cn",
    provider: str = "auto",
) -> dict:
    """List available industries for a market/provider."""
    if provider in ("auto", "tushare") and market == "cn":
        return list_cn_industries()

    return {
        "success": False,
        "provider": provider,
        "market": market,
        "error_type": "unsupported_market",
        "message": f"Unsupported industry list provider combination: market={market}, provider={provider}",
        "industries": [],
    }


def get_industry_members(
    industry: str,
    market: str = "cn",
    provider: str = "auto",
    match_mode: str = "fuzzy",
    limit: int | None = None,
) -> IndustryMembersResult:
    """Fetch industry members through the unified data layer."""
    if provider in ("auto", "tushare") and market == "cn":
        return get_cn_industry_members(
            industry=industry,
            match_mode=match_mode,
            limit=limit,
        )

    return IndustryMembersResult(
        success=False,
        industry=industry,
        provider=provider,
        market=market,
        error_type="unsupported_market",
        message=(
            "Unsupported industry member provider combination: "
            f"market={market}, provider={provider}"
        ),
    )

