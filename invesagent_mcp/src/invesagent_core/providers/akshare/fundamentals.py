from __future__ import annotations

import pandas as pd

from invesagent_core.models.fundamentals import FundamentalRecord, FundamentalsResult
from invesagent_core.providers.akshare.client import get_client
from invesagent_core.services.data.common import classify_provider_error, normalize_cn_code


_DATA_TYPE_TO_SINA = {
    "income": "利润表",
    "balancesheet": "资产负债表",
    "cashflow": "现金流量表",
}


def _to_records(
    df: pd.DataFrame,
    symbol: str,
    data_type: str,
    asset_type: str,
) -> list[FundamentalRecord]:
    if df is None or df.empty:
        return []

    working = df.fillna("")
    date_columns = ["报告日", "报告日期", "日期", "end_date"]
    records: list[FundamentalRecord] = []

    for item in working.to_dict(orient="records"):
        period = next((str(item.get(column)) for column in date_columns if item.get(column)), None)
        if period:
            period = period.replace("-", "")[:8]
        records.append(
            FundamentalRecord(
                symbol=symbol,
                period=period,
                statement_type=data_type,
                provider="akshare",
                market="cn",
                asset_type=asset_type,
                raw=item,
            )
        )

    return records


def get_akshare_fundamentals(
    symbol: str,
    start_date: str,
    end_date: str,
    data_type: str,
    asset_type: str = "stock",
) -> FundamentalsResult:
    """Fetch China A-share fundamentals from AKShare when available."""
    normalized_data_type = data_type.strip().lower()
    code = normalize_cn_code(symbol)

    try:
        ak = get_client()
        if normalized_data_type in _DATA_TYPE_TO_SINA:
            api_name = "stock_financial_report_sina"
            df = ak.stock_financial_report_sina(
                stock=code,
                symbol=_DATA_TYPE_TO_SINA[normalized_data_type],
            )
        elif normalized_data_type == "fina_indicator":
            api_name = "stock_financial_analysis_indicator"
            df = ak.stock_financial_analysis_indicator(symbol=code)
        else:
            return FundamentalsResult(
                success=False,
                symbol=symbol,
                start_date=start_date,
                end_date=end_date,
                provider="akshare",
                market="cn",
                asset_type=asset_type,
                data_type=data_type,
                error_type="unsupported_fundamental_data_type",
                message="data_type must be one of income, balancesheet, cashflow, fina_indicator.",
            )
    except Exception as exc:
        error_type, message = classify_provider_error(exc, "AKShare", locals().get("api_name", "fundamentals"))
        return FundamentalsResult(
            success=False,
            symbol=symbol,
            start_date=start_date,
            end_date=end_date,
            provider="akshare",
            market="cn",
            asset_type=asset_type,
            data_type=normalized_data_type,
            error_type=error_type,
            message=message,
            raw={"raw_error": str(exc)},
        )

    records = _to_records(df, symbol=symbol, data_type=normalized_data_type, asset_type=asset_type)
    if start_date or end_date:
        records = [
            record
            for record in records
            if (not start_date or not record.period or record.period >= start_date)
            and (not end_date or not record.period or record.period <= end_date)
        ]

    if not records:
        return FundamentalsResult(
            success=False,
            symbol=symbol,
            start_date=start_date,
            end_date=end_date,
            provider="akshare",
            market="cn",
            asset_type=asset_type,
            data_type=normalized_data_type,
            error_type="empty_data",
            message=f"No AKShare {api_name} data returned.",
        )

    return FundamentalsResult(
        success=True,
        symbol=symbol,
        start_date=start_date,
        end_date=end_date,
        provider="akshare",
        market="cn",
        asset_type=asset_type,
        data_type=normalized_data_type,
        records=records,
    )
