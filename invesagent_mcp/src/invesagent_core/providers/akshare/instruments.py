from __future__ import annotations

import re

from invesagent_core.models.instruments import Instrument


_CN_CODE_RE = re.compile(r"^\d{6}(\.(SH|SZ|BJ))?$", re.IGNORECASE)
_HK_CODE_RE = re.compile(r"^\d{5}$")
_US_SYMBOL_RE = re.compile(r"^[A-Z]{1,6}([.-][A-Z]{1,4})?$", re.IGNORECASE)


def normalize_cn_symbol(symbol: str) -> str:
    """Normalize a China-market symbol to the pure code AKShare expects."""
    value = symbol.strip().upper()
    return value.split(".")[0]


def normalize_hk_symbol(symbol: str) -> str:
    """Normalize a Hong Kong stock symbol to five digits."""
    value = symbol.strip().upper().replace(".HK", "")

    if value.isdigit():
        return value.zfill(5)

    return value


def normalize_us_symbol(symbol: str) -> str:
    """Normalize a US stock symbol for AKShare."""
    return symbol.strip().upper()


def maybe_resolve_akshare_instrument(
    query: str,
    market: str | None = None,
    asset_type: str | None = None,
) -> Instrument | None:
    """Resolve simple AKShare-supported symbols without remote lookups."""
    value = query.strip()
    upper = value.upper()

    if market == "cn" or _CN_CODE_RE.match(upper):
        symbol = upper if "." in upper else value
        normalized_asset_type = asset_type or "stock"
        return Instrument(
            symbol=symbol,
            name=None,
            market="cn",
            asset_type=normalized_asset_type,
            currency="CNY",
            provider="akshare",
            raw={"input": query, "akshare_symbol": normalize_cn_symbol(symbol)},
        )

    if market == "hk" or _HK_CODE_RE.match(upper) or upper.endswith(".HK"):
        symbol = normalize_hk_symbol(upper)
        return Instrument(
            symbol=symbol,
            name=None,
            market="hk",
            asset_type=asset_type or "stock",
            exchange="HKEX",
            currency="HKD",
            provider="akshare",
            raw={"input": query, "akshare_symbol": symbol},
        )

    if market == "us" or _US_SYMBOL_RE.match(upper):
        symbol = normalize_us_symbol(upper)
        return Instrument(
            symbol=symbol,
            name=symbol,
            market="us",
            asset_type=asset_type or "stock",
            currency="USD",
            provider="akshare",
            raw={"input": query, "akshare_symbol": symbol},
        )

    return None

