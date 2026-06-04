from __future__ import annotations

from invesagent_core.models.alternative_data import AlternativeDataResult
from invesagent_core.services.data.alternative_data import get_alternative_data


def get_news_or_research(
    symbol: str | None = None,
    market: str = "cn",
    provider: str = "auto",
    keyword: str = "news",
    start_date: str | None = None,
    end_date: str | None = None,
    limit: int = 50,
) -> AlternativeDataResult:
    """Fetch news or research report metadata where supported."""
    category = "research_reports" if keyword in {"research", "report", "研报"} else "news"
    return get_alternative_data(
        category=category,
        market=market,
        symbol=symbol,
        provider=provider,
        keyword=keyword,
        start_date=start_date,
        end_date=end_date,
        limit=limit,
    )
