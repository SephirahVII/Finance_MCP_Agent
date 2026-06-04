from __future__ import annotations

from typing import Any

import pandas as pd

from invesagent_core.models.alternative_data import AlternativeDataRecord, AlternativeDataResult
from invesagent_core.providers.tushare.client import get_client
from invesagent_core.services.data.common import classify_provider_error


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


def _normalize_date(value) -> str | None:
    if value is None or value == "":
        return None
    text = str(value).replace("-", "")
    return text[:8] if text else None


def _records_from_df(
    *,
    df: pd.DataFrame,
    category: str,
    provider: str,
    market: str,
    symbol: str | None,
    date_fields: list[str],
    title_fields: list[str] | None = None,
    name_fields: list[str] | None = None,
    value_fields: list[str] | None = None,
    url_fields: list[str] | None = None,
) -> list[AlternativeDataRecord]:
    if df is None or df.empty:
        return []

    records: list[AlternativeDataRecord] = []
    for item in df.fillna("").to_dict(orient="records"):
        date = next((_normalize_date(item.get(field)) for field in date_fields if item.get(field)), None)
        title = next((str(item.get(field)) for field in (title_fields or []) if item.get(field)), None)
        name = next((str(item.get(field)) for field in (name_fields or []) if item.get(field)), None)
        value = next((_to_float(item.get(field)) for field in (value_fields or []) if item.get(field) != ""), None)
        url = next((str(item.get(field)) for field in (url_fields or []) if item.get(field)), None)
        records.append(
            AlternativeDataRecord(
                category=category,
                symbol=str(item.get("ts_code") or symbol or "") or None,
                date=date,
                end_date=_normalize_date(item.get("end_date")),
                name=name,
                title=title,
                value=value,
                metrics={key: value for key, value in item.items() if key not in {"ts_code"}},
                url=url,
                provider=provider,
                market=market,
                raw=item,
            )
        )
    return records


def _call_pro(api_name: str, **kwargs: Any) -> pd.DataFrame:
    pro = get_client()
    api = getattr(pro, api_name)
    return api(**{key: value for key, value in kwargs.items() if value not in (None, "")})


def _result(
    *,
    category: str,
    market: str,
    symbol: str | None,
    start_date: str | None,
    end_date: str | None,
    records: list[AlternativeDataRecord] | None = None,
    error_type: str | None = None,
    message: str | None = None,
    raw: dict | None = None,
) -> AlternativeDataResult:
    return AlternativeDataResult(
        success=bool(records),
        category=category,
        provider="tushare",
        market=market,
        symbol=symbol,
        start_date=start_date,
        end_date=end_date,
        records=records or [],
        error_type=None if records else error_type or "empty_data",
        message=None if records else message or "No Tushare data returned.",
        raw=raw,
    )


def fetch_tushare_alternative_data(
    *,
    category: str,
    market: str = "cn",
    symbol: str | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
    keyword: str | None = None,
    limit: int | None = None,
) -> AlternativeDataResult:
    """Fetch non-core datasets from Tushare and normalize to AlternativeDataResult."""
    try:
        if category == "announcements":
            df = _call_pro("anns_d", ts_code=symbol, start_date=start_date, end_date=end_date, title=keyword)
            records = _records_from_df(
                df=df,
                category=category,
                provider="tushare",
                market=market,
                symbol=symbol,
                date_fields=["ann_date", "pub_time"],
                title_fields=["title"],
                name_fields=["name"],
                url_fields=["url"],
            )
        elif category == "financial_disclosure_dates":
            df = _call_pro("disclosure_date", ts_code=symbol, start_date=start_date, end_date=end_date)
            records = _records_from_df(
                df=df,
                category=category,
                provider="tushare",
                market=market,
                symbol=symbol,
                date_fields=["ann_date", "pre_date", "actual_date"],
                title_fields=["modify_date"],
            )
        elif category == "dividends":
            df = _call_pro("dividend", ts_code=symbol, ann_date=start_date, end_date=end_date)
            records = _records_from_df(
                df=df,
                category=category,
                provider="tushare",
                market=market,
                symbol=symbol,
                date_fields=["ann_date", "ex_date", "record_date", "pay_date"],
                title_fields=["div_proc"],
                value_fields=["cash_div", "stk_div"],
            )
        elif category == "shareholder_counts":
            df = _call_pro("stk_holdernumber", ts_code=symbol, start_date=start_date, end_date=end_date)
            records = _records_from_df(
                df=df,
                category=category,
                provider="tushare",
                market=market,
                symbol=symbol,
                date_fields=["ann_date", "end_date"],
                value_fields=["holder_num"],
            )
        elif category == "top_shareholders":
            df = _call_pro("top10_holders", ts_code=symbol, start_date=start_date, end_date=end_date)
            records = _records_from_df(
                df=df,
                category=category,
                provider="tushare",
                market=market,
                symbol=symbol,
                date_fields=["ann_date", "end_date"],
                name_fields=["holder_name"],
                value_fields=["hold_amount", "hold_ratio"],
            )
        elif category == "float_top_shareholders":
            df = _call_pro("top10_floatholders", ts_code=symbol, start_date=start_date, end_date=end_date)
            records = _records_from_df(
                df=df,
                category=category,
                provider="tushare",
                market=market,
                symbol=symbol,
                date_fields=["ann_date", "end_date"],
                name_fields=["holder_name"],
                value_fields=["hold_amount", "hold_ratio"],
            )
        elif category == "northbound_capital":
            df = _call_pro("moneyflow_hsgt", start_date=start_date, end_date=end_date)
            records = _records_from_df(
                df=df,
                category=category,
                provider="tushare",
                market=market,
                symbol=symbol,
                date_fields=["trade_date"],
                value_fields=["north_money", "south_money"],
            )
        elif category == "money_flow":
            df = _call_pro("moneyflow", ts_code=symbol, start_date=start_date, end_date=end_date)
            records = _records_from_df(
                df=df,
                category=category,
                provider="tushare",
                market=market,
                symbol=symbol,
                date_fields=["trade_date"],
                value_fields=["net_mf_amount", "buy_sm_amount", "buy_lg_amount", "buy_elg_amount"],
            )
        elif category == "dragon_tiger":
            df = _call_pro("top_list", ts_code=symbol, start_date=start_date, end_date=end_date)
            records = _records_from_df(
                df=df,
                category=category,
                provider="tushare",
                market=market,
                symbol=symbol,
                date_fields=["trade_date"],
                title_fields=["exalter"],
                value_fields=["amount", "net_amount", "buy", "sell"],
            )
        elif category == "block_trades":
            df = _call_pro("block_trade", ts_code=symbol, start_date=start_date, end_date=end_date)
            records = _records_from_df(
                df=df,
                category=category,
                provider="tushare",
                market=market,
                symbol=symbol,
                date_fields=["trade_date"],
                value_fields=["price", "vol", "amount"],
            )
        elif category == "index_weights":
            df = _call_pro("index_weight", index_code=symbol, start_date=start_date, end_date=end_date)
            records = _records_from_df(
                df=df,
                category=category,
                provider="tushare",
                market=market,
                symbol=symbol,
                date_fields=["trade_date"],
                name_fields=["con_code"],
                value_fields=["weight"],
            )
        elif category == "research_reports":
            df = _call_pro("report_rc", ts_code=symbol, start_date=start_date, end_date=end_date)
            records = _records_from_df(
                df=df,
                category=category,
                provider="tushare",
                market=market,
                symbol=symbol,
                date_fields=["report_date"],
                title_fields=["title"],
                name_fields=["org_name", "analyst"],
                value_fields=["rating"],
            )
        elif category == "macro":
            api_name = _macro_api(keyword)
            df = _call_pro(api_name, start_m=start_date, end_m=end_date)
            records = _records_from_df(
                df=df,
                category=category,
                provider="tushare",
                market=market,
                symbol=symbol,
                date_fields=["month", "quarter", "date", "trade_date"],
                value_fields=["value", "nt_val", "nt_yoy", "nt_mom", "pmi", "cpi"],
            )
        else:
            return AlternativeDataResult(
                success=False,
                category=category,
                provider="tushare",
                market=market,
                symbol=symbol,
                start_date=start_date,
                end_date=end_date,
                error_type="unsupported_category",
                message=f"Unsupported Tushare alternative data category: {category}",
            )
    except Exception as exc:
        error_type, message = classify_provider_error(exc, "Tushare", category)
        return AlternativeDataResult(
            success=False,
            category=category,
            provider="tushare",
            market=market,
            symbol=symbol,
            start_date=start_date,
            end_date=end_date,
            error_type=error_type,
            message=message,
            raw={"raw_error": str(exc)},
        )

    if limit and limit > 0:
        records = records[:limit]
    return _result(
        category=category,
        market=market,
        symbol=symbol,
        start_date=start_date,
        end_date=end_date,
        records=records,
    )


def _macro_api(keyword: str | None) -> str:
    value = (keyword or "").strip().lower()
    if value in {"cpi", "inflation"}:
        return "cn_cpi"
    if value in {"pmi"}:
        return "cn_pmi"
    if value in {"money_supply", "m2", "m1", "m0"}:
        return "cn_m"
    if value in {"shibor", "interest_rate", "rate"}:
        return "shibor"
    if value in {"social_financing", "sf", "社融"}:
        return "sf_month"
    return "cn_cpi"
