from __future__ import annotations

import pandas as pd

from invesagent_core.models.fundamentals import FundamentalRecord, FundamentalsResult
from invesagent_core.providers.tushare.client import get_client


_DATA_TYPE_TO_API = {
    "income": "income",
    "balancesheet": "balancesheet",
    "cashflow": "cashflow",
    "fina_indicator": "fina_indicator",
}


def _classify_tushare_error(error: Exception, api_name: str) -> tuple[str, str]:
    raw_error = str(error)

    if "没有接口" in raw_error or "权限" in raw_error:
        return "permission_denied", f"Current Tushare token does not have {api_name} access."

    if "频率" in raw_error or "超限" in raw_error:
        return "rate_limited", f"Tushare {api_name} request is rate limited."

    return "tushare_error", f"Failed to fetch Tushare {api_name} data."


def _to_records(
    df: pd.DataFrame,
    symbol: str,
    data_type: str,
    asset_type: str,
) -> list[FundamentalRecord]:
    if df is None or df.empty:
        return []

    sort_column = "end_date" if "end_date" in df.columns else "ann_date"
    df = df.sort_values(sort_column).fillna("")
    records: list[FundamentalRecord] = []

    for item in df.to_dict(orient="records"):
        records.append(
            FundamentalRecord(
                symbol=symbol,
                period=str(item.get("end_date")) if item.get("end_date") else None,
                ann_date=str(item.get("ann_date")) if item.get("ann_date") else None,
                report_type=str(item.get("report_type")) if item.get("report_type") else None,
                statement_type=data_type,
                provider="tushare",
                market="cn",
                asset_type=asset_type,
                raw=item,
            )
        )

    return records


def get_cn_fundamentals(
    symbol: str,
    start_date: str,
    end_date: str,
    data_type: str,
    asset_type: str = "stock",
) -> FundamentalsResult:
    """Fetch Tushare financial statement or indicator records."""
    normalized_data_type = data_type.strip().lower()
    api_name = _DATA_TYPE_TO_API.get(normalized_data_type)

    if api_name is None:
        return FundamentalsResult(
            success=False,
            symbol=symbol,
            start_date=start_date,
            end_date=end_date,
            provider="tushare",
            market="cn",
            asset_type=asset_type,
            data_type=data_type,
            error_type="unsupported_fundamental_data_type",
            message="data_type must be one of income, balancesheet, cashflow, fina_indicator.",
        )

    pro = get_client()

    try:
        api = getattr(pro, api_name)
        df = api(
            ts_code=symbol,
            start_date=start_date,
            end_date=end_date,
        )
    except Exception as exc:
        error_type, message = _classify_tushare_error(exc, api_name)
        return FundamentalsResult(
            success=False,
            symbol=symbol,
            start_date=start_date,
            end_date=end_date,
            provider="tushare",
            market="cn",
            asset_type=asset_type,
            data_type=normalized_data_type,
            error_type=error_type,
            message=message,
            raw={"raw_error": str(exc)},
        )

    records = _to_records(
        df=df,
        symbol=symbol,
        data_type=normalized_data_type,
        asset_type=asset_type,
    )

    if not records:
        return FundamentalsResult(
            success=False,
            symbol=symbol,
            start_date=start_date,
            end_date=end_date,
            provider="tushare",
            market="cn",
            asset_type=asset_type,
            data_type=normalized_data_type,
            error_type="empty_data",
            message=f"No Tushare {api_name} data returned.",
        )

    return FundamentalsResult(
        success=True,
        symbol=symbol,
        start_date=start_date,
        end_date=end_date,
        provider="tushare",
        market="cn",
        asset_type=asset_type,
        data_type=normalized_data_type,
        records=records,
    )
