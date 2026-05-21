from __future__ import annotations

from invesagent_core.models.fundamentals import FundamentalsResult
from invesagent_core.providers.tushare.fundamentals import get_cn_fundamentals
from invesagent_core.utils.dates import normalize_yyyymmdd_date


def get_fundamentals(
    symbol: str,
    market: str,
    data_type: str,
    start_date: str,
    end_date: str,
    asset_type: str = "stock",
    provider: str = "auto",
) -> FundamentalsResult:
    """Unified fundamentals data service."""
    start_date = normalize_yyyymmdd_date(start_date)
    end_date = normalize_yyyymmdd_date(end_date)

    if provider in ("auto", "tushare") and market == "cn" and asset_type == "stock":
        return get_cn_fundamentals(
            symbol=symbol,
            start_date=start_date,
            end_date=end_date,
            data_type=data_type,
            asset_type=asset_type,
        )

    return FundamentalsResult(
        success=False,
        symbol=symbol,
        start_date=start_date,
        end_date=end_date,
        provider=provider,
        market=market,
        asset_type=asset_type,
        data_type=data_type,
        error_type="unsupported_market",
        message=(
            "Unsupported fundamentals provider combination: "
            f"market={market}, asset_type={asset_type}, provider={provider}"
        ),
    )
