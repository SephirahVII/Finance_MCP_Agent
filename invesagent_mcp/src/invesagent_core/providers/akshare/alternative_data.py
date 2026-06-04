from __future__ import annotations

from typing import Any

import pandas as pd

from invesagent_core.models.alternative_data import AlternativeDataRecord, AlternativeDataResult
from invesagent_core.providers.akshare.client import get_client
from invesagent_core.services.data.common import classify_provider_error, normalize_cn_code


def _to_float(value) -> float | None:
    if value is None or value == "":
        return None
    try:
        converted = float(str(value).replace(",", "").replace("%", ""))
    except (TypeError, ValueError):
        return None
    if pd.isna(converted):
        return None
    return converted


def _normalize_date(value) -> str | None:
    if value is None or value == "":
        return None
    try:
        parsed = pd.to_datetime(value)
    except Exception:
        text = str(value).replace("-", "")
        return text[:8] if text else None
    if pd.isna(parsed):
        return None
    return parsed.strftime("%Y%m%d")


def _pick(item: dict, names: list[str]):
    for name in names:
        if name in item:
            return item.get(name)
    return None


def _records_from_df(
    *,
    df: pd.DataFrame,
    category: str,
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
        date = _normalize_date(_pick(item, date_fields))
        title = _pick(item, title_fields or [])
        name = _pick(item, name_fields or [])
        value = _to_float(_pick(item, value_fields or []))
        url = _pick(item, url_fields or [])
        records.append(
            AlternativeDataRecord(
                category=category,
                symbol=str(_pick(item, ["代码", "股票代码", "symbol", "code"]) or symbol or "") or None,
                date=date,
                end_date=_normalize_date(_pick(item, ["报告期", "截止日期", "end_date"])),
                name=str(name) if name else None,
                title=str(title) if title else None,
                value=value,
                metrics=item,
                url=str(url) if url else None,
                provider="akshare",
                market=market,
                raw=item,
            )
        )
    return records


def _try_call(ak, candidates: list[tuple[str, dict[str, Any]]]) -> tuple[str, pd.DataFrame]:
    last_error: Exception | None = None
    for name, kwargs in candidates:
        try:
            api = getattr(ak, name)
            return name, api(**{key: value for key, value in kwargs.items() if value not in (None, "")})
        except Exception as exc:
            last_error = exc
    if last_error:
        raise last_error
    raise AttributeError("No AKShare candidates configured.")


def fetch_akshare_alternative_data(
    *,
    category: str,
    market: str = "cn",
    symbol: str | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
    keyword: str | None = None,
    limit: int | None = None,
) -> AlternativeDataResult:
    """Fetch non-core datasets from AKShare and normalize to AlternativeDataResult."""
    code = normalize_cn_code(symbol or "")
    try:
        ak = get_client()
        if category == "announcements":
            api_name, df = _try_call(
                ak,
                [
                    ("stock_notice_report", {"symbol": keyword or "全部"}),
                    ("stock_zh_a_disclosure_report_cninfo", {"symbol": code, "market": "沪深京"}),
                ],
            )
            records = _records_from_df(
                df=df,
                category=category,
                market=market,
                symbol=symbol,
                date_fields=["公告日期", "公告时间", "date"],
                title_fields=["公告标题", "标题", "title"],
                name_fields=["股票简称", "名称"],
                url_fields=["公告链接", "url"],
            )
        elif category == "financial_disclosure_dates":
            api_name, df = _try_call(
                ak,
                [
                    ("stock_report_disclosure", {"symbol": "沪深京", "date": start_date}),
                    ("stock_yjbb_em", {"date": start_date}),
                ],
            )
            records = _records_from_df(
                df=df,
                category=category,
                market=market,
                symbol=symbol,
                date_fields=["公告日期", "预约披露日期", "最新公告日期"],
                title_fields=["报告期"],
            )
        elif category == "dividends":
            api_name, df = _try_call(
                ak,
                [
                    ("stock_history_dividend_detail", {"symbol": code, "indicator": "分红"}),
                    ("stock_history_dividend", {}),
                ],
            )
            records = _records_from_df(
                df=df,
                category=category,
                market=market,
                symbol=symbol,
                date_fields=["公告日期", "除权除息日", "股权登记日"],
                title_fields=["方案", "进度"],
                value_fields=["派息", "送股", "转增"],
            )
        elif category == "shareholder_counts":
            api_name, df = _try_call(
                ak,
                [
                    ("stock_zh_a_gdhs", {"symbol": code}),
                    ("stock_gdhs_detail_em", {"symbol": code}),
                ],
            )
            records = _records_from_df(
                df=df,
                category=category,
                market=market,
                symbol=symbol,
                date_fields=["股东户数统计截止日", "截止日期", "公告日期"],
                value_fields=["股东户数", "户均持股数量"],
            )
        elif category in {"top_shareholders", "float_top_shareholders"}:
            api_name, df = _try_call(
                ak,
                [
                    ("stock_gdfx_top_10_em", {"symbol": code}),
                    ("stock_gdfx_free_top_10_em", {"symbol": code}),
                ],
            )
            records = _records_from_df(
                df=df,
                category=category,
                market=market,
                symbol=symbol,
                date_fields=["报告期", "公告日期"],
                name_fields=["股东名称"],
                value_fields=["持股数量", "持股比例"],
            )
        elif category == "northbound_capital":
            api_name, df = _try_call(
                ak,
                [
                    ("stock_hsgt_hist_em", {"symbol": "北向资金"}),
                    ("stock_hsgt_north_net_flow_in_em", {"symbol": "北上"}),
                ],
            )
            records = _records_from_df(
                df=df,
                category=category,
                market=market,
                symbol=symbol,
                date_fields=["日期"],
                value_fields=["当日成交净买额", "净流入", "value"],
            )
        elif category == "money_flow":
            api_name, df = _try_call(
                ak,
                [
                    ("stock_individual_fund_flow", {"stock": code, "market": "sh" if code.startswith("6") else "sz"}),
                    ("stock_fund_flow_individual", {"symbol": "即时"}),
                ],
            )
            records = _records_from_df(
                df=df,
                category=category,
                market=market,
                symbol=symbol,
                date_fields=["日期"],
                value_fields=["主力净流入-净额", "净流入", "净额"],
            )
        elif category == "dragon_tiger":
            api_name, df = _try_call(
                ak,
                [
                    ("stock_lhb_detail_daily_sina", {"date": start_date}),
                    ("stock_lhb_detail_em", {"start_date": start_date, "end_date": end_date}),
                ],
            )
            records = _records_from_df(
                df=df,
                category=category,
                market=market,
                symbol=symbol,
                date_fields=["上榜日", "交易日期", "日期"],
                title_fields=["解读", "上榜原因"],
                value_fields=["龙虎榜净买额", "买入额", "卖出额"],
            )
        elif category == "block_trades":
            api_name, df = _try_call(
                ak,
                [
                    ("stock_dzjy_mrmx", {"symbol": "A股", "start_date": start_date, "end_date": end_date}),
                    ("stock_block_trade_em", {}),
                ],
            )
            records = _records_from_df(
                df=df,
                category=category,
                market=market,
                symbol=symbol,
                date_fields=["交易日期", "日期"],
                value_fields=["成交价", "成交量", "成交额"],
            )
        elif category == "index_weights":
            api_name, df = _try_call(
                ak,
                [
                    ("index_stock_cons_weight_csindex", {"symbol": symbol or keyword}),
                    ("index_stock_cons", {"symbol": symbol or keyword}),
                ],
            )
            records = _records_from_df(
                df=df,
                category=category,
                market=market,
                symbol=symbol,
                date_fields=["日期"],
                name_fields=["成分券代码", "品种代码", "代码"],
                value_fields=["权重", "权重(%)"],
            )
        elif category == "sector_quotes":
            api_name, df = _try_call(
                ak,
                [
                    ("stock_board_industry_name_em", {}),
                    ("stock_board_concept_name_em", {}),
                ],
            )
            records = _records_from_df(
                df=df,
                category=category,
                market=market,
                symbol=symbol,
                date_fields=["日期"],
                name_fields=["板块名称", "名称"],
                value_fields=["涨跌幅", "成交额", "换手率"],
            )
        elif category in {"news", "research_reports"}:
            api_name, df = _try_call(
                ak,
                [
                    ("stock_news_em", {"symbol": code}),
                    ("stock_research_report_em", {"symbol": code}),
                ],
            )
            records = _records_from_df(
                df=df,
                category=category,
                market=market,
                symbol=symbol,
                date_fields=["发布时间", "日期"],
                title_fields=["新闻标题", "标题", "研报标题"],
                name_fields=["文章来源", "机构", "分析师"],
                url_fields=["新闻链接", "链接"],
            )
        elif category == "macro":
            api_name = _macro_api(keyword)
            api = getattr(ak, api_name)
            df = api()
            records = _records_from_df(
                df=df,
                category=category,
                market=market,
                symbol=symbol,
                date_fields=["月份", "日期", "时间"],
                value_fields=["今值", "数值", "value"],
            )
        else:
            return AlternativeDataResult(
                success=False,
                category=category,
                provider="akshare",
                market=market,
                symbol=symbol,
                start_date=start_date,
                end_date=end_date,
                error_type="unsupported_category",
                message=f"Unsupported AKShare alternative data category: {category}",
            )
    except Exception as exc:
        error_type, message = classify_provider_error(exc, "AKShare", category)
        return AlternativeDataResult(
            success=False,
            category=category,
            provider="akshare",
            market=market,
            symbol=symbol,
            start_date=start_date,
            end_date=end_date,
            error_type=error_type,
            message=message,
            raw={"raw_error": str(exc)},
        )

    if start_date or end_date:
        records = [
            record
            for record in records
            if (not start_date or not record.date or record.date >= start_date)
            and (not end_date or not record.date or record.date <= end_date)
        ]
    if limit and limit > 0:
        records = records[:limit]
    return AlternativeDataResult(
        success=bool(records),
        category=category,
        provider="akshare",
        market=market,
        symbol=symbol,
        start_date=start_date,
        end_date=end_date,
        records=records,
        error_type=None if records else "empty_data",
        message=None if records else f"No AKShare {locals().get('api_name', category)} data returned.",
    )


def _macro_api(keyword: str | None) -> str:
    value = (keyword or "").strip().lower()
    if value in {"cpi", "inflation"}:
        return "macro_china_cpi"
    if value in {"pmi"}:
        return "macro_china_pmi"
    if value in {"money_supply", "m2", "m1", "m0"}:
        return "macro_china_money_supply"
    if value in {"social_financing", "sf", "社融"}:
        return "macro_china_shrzgm"
    if value in {"fx", "exchange_rate", "汇率"}:
        return "currency_boc_sina"
    if value in {"commodity", "商品"}:
        return "futures_spot_price"
    return "macro_china_cpi"
