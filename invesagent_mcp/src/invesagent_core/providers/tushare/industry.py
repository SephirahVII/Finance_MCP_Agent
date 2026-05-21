from __future__ import annotations

from invesagent_core.models.industry import IndustryMember, IndustryMembersResult
from invesagent_core.providers.tushare.instruments import get_stock_basic


def list_cn_industries() -> dict:
    """List industries available from cached/fetched Tushare stock_basic data."""
    try:
        stocks = get_stock_basic()
    except Exception as exc:
        return {
            "success": False,
            "provider": "tushare",
            "market": "cn",
            "error_type": "tushare_error",
            "message": "Failed to fetch Tushare stock_basic industry data.",
            "raw": {"raw_error": str(exc)},
            "industries": [],
        }

    industries = sorted(
        {
            str(item.get("industry")).strip()
            for item in stocks
            if item.get("industry") and str(item.get("industry")).strip()
        }
    )

    return {
        "success": True,
        "provider": "tushare",
        "market": "cn",
        "count": len(industries),
        "industries": industries,
    }


def get_cn_industry_members(
    industry: str,
    match_mode: str = "fuzzy",
    limit: int | None = None,
) -> IndustryMembersResult:
    """Fetch China A-share industry members from Tushare stock_basic."""
    query = industry.strip()

    if not query:
        return IndustryMembersResult(
            success=False,
            industry=industry,
            provider="tushare",
            market="cn",
            error_type="empty_industry",
            message="Industry query is empty.",
        )

    try:
        stocks = get_stock_basic()
    except Exception as exc:
        return IndustryMembersResult(
            success=False,
            industry=industry,
            provider="tushare",
            market="cn",
            error_type="tushare_error",
            message="Failed to fetch Tushare stock_basic industry data.",
            warnings=[str(exc)],
        )

    normalized_mode = match_mode.strip().lower()

    if normalized_mode == "exact":
        matched = [item for item in stocks if str(item.get("industry", "")).strip() == query]
    else:
        matched = [item for item in stocks if query in str(item.get("industry", "")).strip()]

    matched_industries = sorted(
        {
            str(item.get("industry")).strip()
            for item in matched
            if item.get("industry") and str(item.get("industry")).strip()
        }
    )

    if limit and limit > 0:
        matched = matched[:limit]

    members = [
        IndustryMember(
            symbol=item.get("ts_code"),
            name=item.get("name"),
            industry=item.get("industry"),
            area=item.get("area"),
            market=item.get("market"),
            list_date=item.get("list_date"),
            provider="tushare",
            raw=item,
        )
        for item in matched
    ]

    if not members:
        return IndustryMembersResult(
            success=False,
            industry=industry,
            provider="tushare",
            market="cn",
            members=[],
            matched_industries=[],
            error_type="empty_data",
            message="No industry members matched.",
        )

    return IndustryMembersResult(
        success=True,
        industry=industry,
        provider="tushare",
        market="cn",
        members=members,
        matched_industries=matched_industries,
    )

