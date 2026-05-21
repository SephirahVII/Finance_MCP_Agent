from __future__ import annotations

from invesagent_core.models.valuation import ValuationResult
from invesagent_core.providers.tushare.valuation import get_cn_daily_basic
from invesagent_core.utils.dates import normalize_yyyymmdd_date


def get_valuation(
    symbol: str,
    market: str,
    asset_type: str = "stock",
    start_date: str = "",
    end_date: str = "",
    provider: str = "auto",
) -> ValuationResult:
    """Unified valuation data service."""
    start_date = normalize_yyyymmdd_date(start_date)
    end_date = normalize_yyyymmdd_date(end_date)

    if provider in ("auto", "tushare") and market == "cn" and asset_type in ("stock", "etf"):
        return get_cn_daily_basic(
            symbol=symbol,
            start_date=start_date,
            end_date=end_date,
            asset_type=asset_type,
        )

    return ValuationResult(
        success=False,
        symbol=symbol,
        start_date=start_date,
        end_date=end_date,
        provider=provider,
        market=market,
        asset_type=asset_type,
        error_type="unsupported_market",
        message=(
            "Unsupported valuation provider combination: "
            f"market={market}, asset_type={asset_type}, provider={provider}"
        ),
    )
