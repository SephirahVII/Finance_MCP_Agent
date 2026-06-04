from __future__ import annotations

from invesagent_core.models.alternative_data import AlternativeDataResult
from invesagent_core.services.data.alternative_data import get_alternative_data


def get_macro_data(
    indicator: str = "cpi",
    market: str = "cn",
    start_date: str | None = None,
    end_date: str | None = None,
    provider: str = "auto",
    limit: int = 100,
) -> AlternativeDataResult:
    """Fetch macro indicators through the unified provider layer."""
    return get_alternative_data(
        category="macro",
        market=market,
        start_date=start_date,
        end_date=end_date,
        provider=provider,
        keyword=indicator,
        limit=limit,
    )
