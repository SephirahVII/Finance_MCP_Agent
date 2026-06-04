from __future__ import annotations

import pandas as pd

from invesagent_core.models.valuation import ValuationRecord, ValuationResult
from invesagent_core.providers.akshare.client import get_client
from invesagent_core.services.data.common import classify_provider_error, normalize_cn_code


def _to_float(value) -> float | None:
    if value is None or value == "":
        return None
    try:
        converted = float(value)
    except (TypeError, ValueError):
        return None
    if pd.isna(converted):
        return None
    return converted


def _normalize_date(value) -> str:
    if value is None or value == "":
        return ""
    try:
        parsed = pd.to_datetime(value)
    except Exception:
        return str(value).replace("-", "")[:8]
    if pd.isna(parsed):
        return str(value).replace("-", "")[:8]
    return parsed.strftime("%Y%m%d")


def _pick(item: dict, names: list[str]):
    for name in names:
        if name in item:
            return item.get(name)
    return None


def _records_from_lg_indicator(df: pd.DataFrame, symbol: str, asset_type: str) -> list[ValuationRecord]:
    if df is None or df.empty:
        return []
    records: list[ValuationRecord] = []
    for item in df.fillna("").to_dict(orient="records"):
        records.append(
            ValuationRecord(
                symbol=symbol,
                trade_time=_normalize_date(_pick(item, ["trade_date", "date", "日期"])),
                pe=_to_float(_pick(item, ["pe", "市盈率", "pe_ratio"])),
                pe_ttm=_to_float(_pick(item, ["pe_ttm", "市盈率TTM"])),
                pb=_to_float(_pick(item, ["pb", "市净率"])),
                ps=_to_float(_pick(item, ["ps", "市销率"])),
                ps_ttm=_to_float(_pick(item, ["ps_ttm", "市销率TTM"])),
                total_mv=_to_float(_pick(item, ["total_mv", "总市值", "总市值(元)"])),
                circ_mv=_to_float(_pick(item, ["circ_mv", "流通市值", "流通市值(元)"])),
                provider="akshare",
                market="cn",
                asset_type=asset_type,
                raw=item,
            )
        )
    return [record for record in records if record.trade_time]


def get_akshare_valuation(
    symbol: str,
    start_date: str,
    end_date: str,
    asset_type: str = "stock",
) -> ValuationResult:
    """Fetch A-share valuation indicators from AKShare when available."""
    code = normalize_cn_code(symbol)
    try:
        ak = get_client()
        api_name = "stock_a_lg_indicator"
        df = ak.stock_a_lg_indicator(symbol=code)
    except Exception as exc:
        error_type, message = classify_provider_error(exc, "AKShare", locals().get("api_name", "valuation"))
        return ValuationResult(
            success=False,
            symbol=symbol,
            start_date=start_date,
            end_date=end_date,
            provider="akshare",
            market="cn",
            asset_type=asset_type,
            error_type=error_type,
            message=message,
            raw={"raw_error": str(exc)},
        )

    records = _records_from_lg_indicator(df, symbol=symbol, asset_type=asset_type)
    records = [
        record
        for record in records
        if (not start_date or record.trade_time >= start_date)
        and (not end_date or record.trade_time <= end_date)
    ]
    if not records:
        return ValuationResult(
            success=False,
            symbol=symbol,
            start_date=start_date,
            end_date=end_date,
            provider="akshare",
            market="cn",
            asset_type=asset_type,
            error_type="empty_data",
            message="No AKShare stock_a_lg_indicator data returned.",
        )

    return ValuationResult(
        success=True,
        symbol=symbol,
        start_date=start_date,
        end_date=end_date,
        provider="akshare",
        market="cn",
        asset_type=asset_type,
        records=records,
    )
