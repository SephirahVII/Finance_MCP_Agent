from __future__ import annotations

from invesagent_core.models.industry import IndustryMember, IndustryMembersResult
from invesagent_core.providers.akshare.client import get_client
from invesagent_core.services.data.common import classify_provider_error


def list_akshare_industries() -> dict:
    """List Eastmoney industry board names from AKShare."""
    try:
        ak = get_client()
        api_name = "stock_board_industry_name_em"
        df = ak.stock_board_industry_name_em()
    except Exception as exc:
        error_type, message = classify_provider_error(exc, "AKShare", locals().get("api_name", "industry_list"))
        return {
            "success": False,
            "provider": "akshare",
            "market": "cn",
            "error_type": error_type,
            "message": message,
            "raw": {"raw_error": str(exc)},
            "industries": [],
        }

    name_column = "板块名称" if "板块名称" in df.columns else "名称" if "名称" in df.columns else None
    industries = sorted(str(item).strip() for item in df[name_column].dropna().tolist()) if name_column else []
    return {
        "success": bool(industries),
        "provider": "akshare",
        "market": "cn",
        "count": len(industries),
        "industries": industries,
        "error_type": None if industries else "empty_data",
        "message": None if industries else "No AKShare industry names returned.",
    }


def get_akshare_industry_members(
    industry: str,
    match_mode: str = "fuzzy",
    limit: int | None = None,
) -> IndustryMembersResult:
    """Fetch Eastmoney industry board constituents from AKShare."""
    query = industry.strip()
    if not query:
        return IndustryMembersResult(
            success=False,
            industry=industry,
            provider="akshare",
            market="cn",
            error_type="empty_industry",
            message="Industry query is empty.",
        )

    industries = list_akshare_industries()
    candidates = industries.get("industries", [])
    if match_mode.strip().lower() == "exact":
        matched_names = [item for item in candidates if item == query]
    else:
        matched_names = [item for item in candidates if query in item or item in query]
    if not matched_names:
        matched_names = [query]

    board_name = sorted(matched_names, key=len)[0]
    try:
        ak = get_client()
        api_name = "stock_board_industry_cons_em"
        df = ak.stock_board_industry_cons_em(symbol=board_name)
    except Exception as exc:
        error_type, message = classify_provider_error(exc, "AKShare", locals().get("api_name", "industry_members"))
        return IndustryMembersResult(
            success=False,
            industry=industry,
            provider="akshare",
            market="cn",
            matched_industries=matched_names,
            error_type=error_type,
            message=message,
            warnings=[str(exc)],
        )

    rows = df.fillna("").to_dict(orient="records")
    if limit and limit > 0:
        rows = rows[:limit]

    members = [
        IndustryMember(
            symbol=str(item.get("代码") or item.get("code") or ""),
            name=str(item.get("名称") or item.get("name") or "") or None,
            industry=board_name,
            provider="akshare",
            market="cn",
            raw=item,
        )
        for item in rows
        if item.get("代码") or item.get("code")
    ]

    if not members:
        return IndustryMembersResult(
            success=False,
            industry=industry,
            provider="akshare",
            market="cn",
            matched_industries=matched_names,
            error_type="empty_data",
            message="No AKShare industry members matched.",
        )

    return IndustryMembersResult(
        success=True,
        industry=industry,
        provider="akshare",
        market="cn",
        members=members,
        matched_industries=matched_names,
    )
