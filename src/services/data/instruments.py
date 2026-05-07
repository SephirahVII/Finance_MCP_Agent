from __future__ import annotations

import re

from src.models.instruments import Instrument
from src.providers.tushare.instruments import resolve_stock_code


_CN_TS_CODE_RE = re.compile(r"^\d{6}\.(SH|SZ|BJ)$", re.IGNORECASE)
_CRYPTO_USDT_RE = re.compile(r"^[A-Z0-9]{2,20}USDT$", re.IGNORECASE)


def _infer_cn_exchange(symbol: str) -> str | None:
    suffix = symbol.upper().split(".")[-1]

    if suffix == "SH":
        return "SSE"
    if suffix == "SZ":
        return "SZSE"
    if suffix == "BJ":
        return "BSE"

    return None


def _infer_cn_asset_type(symbol: str) -> str:
    """Infer CN asset type roughly from symbol."""
    code = symbol.split(".")[0]

    if code.startswith(("000", "399")):
        return "index"

    if code.startswith(("510", "511", "512", "513", "515", "516", "518", "159")):
        return "etf"

    return "stock"


def _resolve_cn_instrument(name_or_code: str) -> Instrument:
    resolved = resolve_stock_code(name_or_code)

    if not resolved.get("matched"):
        return Instrument(
            symbol=name_or_code,
            name=None,
            market="unknown",
            asset_type="unknown",
            provider="auto",
            raw=resolved,
        )

    symbol = resolved["ts_code"]

    return Instrument(
        symbol=symbol,
        name=resolved.get("name"),
        market="cn",
        asset_type=_infer_cn_asset_type(symbol),
        exchange=_infer_cn_exchange(symbol),
        currency="CNY",
        provider="tushare",
        raw=resolved,
    )


def _resolve_crypto_instrument(symbol: str) -> Instrument:
    normalized = symbol.strip().upper()

    return Instrument(
        symbol=normalized,
        name=normalized,
        market="crypto",
        asset_type="crypto_spot",
        exchange="BINANCE",
        currency="USDT",
        provider="binance",
        raw={"input": symbol, "match_type": "crypto_usdt_symbol"},
    )


def resolve_instrument(
    query: str,
    market: str | None = None,
    asset_type: str | None = None,
    provider: str = "auto",
) -> Instrument:
    """Resolve user input to a unified Instrument."""
    value = query.strip()

    if not value:
        return Instrument(
            symbol=query,
            name=None,
            market="unknown",
            asset_type="unknown",
            provider=provider,
            raw={"error_type": "empty_input"},
        )

    upper = value.upper()

    if market == "crypto" or _CRYPTO_USDT_RE.match(upper):
        return _resolve_crypto_instrument(upper)

    if market == "cn" or _CN_TS_CODE_RE.match(upper) or re.match(r"^\d{6}$", upper):
        return _resolve_cn_instrument(value)

    if market is None:
        resolved = _resolve_cn_instrument(value)
        if resolved.market != "unknown":
            return resolved

    return Instrument(
        symbol=value,
        name=None,
        market="unknown",
        asset_type="unknown",
        provider=provider,
        raw={
            "input": query,
            "message": "Unable to resolve instrument with current providers.",
        },
    )
