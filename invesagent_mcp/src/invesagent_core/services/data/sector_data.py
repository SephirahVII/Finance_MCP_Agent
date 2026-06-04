from __future__ import annotations

from invesagent_core.models.alternative_data import AlternativeDataResult
from invesagent_core.services.data.alternative_data import get_alternative_data


def get_sector_quotes(
    market: str = "cn",
    provider: str = "auto",
    keyword: str | None = None,
    limit: int = 100,
) -> AlternativeDataResult:
    """Fetch industry/concept sector quote snapshots."""
    return get_alternative_data(
        category="sector_quotes",
        market=market,
        provider=provider,
        keyword=keyword,
        limit=limit,
    )
