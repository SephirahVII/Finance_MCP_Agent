from __future__ import annotations

from invesagent_core.models.alternative_data import AlternativeDataResult
from invesagent_core.services.data.alternative_data import get_alternative_data


def get_index_weights(
    index_code: str,
    market: str = "cn",
    start_date: str | None = None,
    end_date: str | None = None,
    provider: str = "auto",
    limit: int = 100,
) -> AlternativeDataResult:
    """Fetch index constituents and weights."""
    return get_alternative_data(
        category="index_weights",
        market=market,
        symbol=index_code,
        start_date=start_date,
        end_date=end_date,
        provider=provider,
        limit=limit,
    )
