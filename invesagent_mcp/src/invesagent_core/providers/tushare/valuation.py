from __future__ import annotations

import pandas as pd

from invesagent_core.models.valuation import ValuationRecord, ValuationResult
from invesagent_core.providers.tushare.client import get_client


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


def _classify_tushare_error(error: Exception) -> tuple[str, str]:
    raw_error = str(error)

    if "没有接口" in raw_error or "权限" in raw_error:
        return (
            "permission_denied",
            "Current Tushare token does not have daily_basic access.",
        )

    if "频率" in raw_error or "超限" in raw_error:
        return (
            "rate_limited",
            "Tushare daily_basic request is rate limited.",
        )

    return (
        "tushare_error",
        "Failed to fetch Tushare daily_basic data.",
    )


def _daily_basic_to_records(df: pd.DataFrame, symbol: str, asset_type: str) -> list[ValuationRecord]:
    if df is None or df.empty:
        return []

    df = df.sort_values("trade_date").fillna("")
    records: list[ValuationRecord] = []

    for item in df.to_dict(orient="records"):
        records.append(
            ValuationRecord(
                symbol=symbol,
                trade_time=str(item.get("trade_date")),
                close=_to_float(item.get("close")),
                turnover_rate=_to_float(item.get("turnover_rate")),
                turnover_rate_f=_to_float(item.get("turnover_rate_f")),
                volume_ratio=_to_float(item.get("volume_ratio")),
                pe=_to_float(item.get("pe")),
                pe_ttm=_to_float(item.get("pe_ttm")),
                pb=_to_float(item.get("pb")),
                ps=_to_float(item.get("ps")),
                ps_ttm=_to_float(item.get("ps_ttm")),
                dv_ratio=_to_float(item.get("dv_ratio")),
                dv_ttm=_to_float(item.get("dv_ttm")),
                total_share=_to_float(item.get("total_share")),
                float_share=_to_float(item.get("float_share")),
                free_share=_to_float(item.get("free_share")),
                total_mv=_to_float(item.get("total_mv")),
                circ_mv=_to_float(item.get("circ_mv")),
                provider="tushare",
                market="cn",
                asset_type=asset_type,
                raw=item,
            )
        )

    return records


def get_cn_daily_basic(
    symbol: str,
    start_date: str,
    end_date: str,
    asset_type: str = "stock",
) -> ValuationResult:
    """Fetch Tushare daily_basic data and return unified valuation records."""
    pro = get_client()

    try:
        df = pro.daily_basic(
            ts_code=symbol,
            start_date=start_date,
            end_date=end_date,
            fields=(
                "ts_code,trade_date,close,turnover_rate,turnover_rate_f,volume_ratio,"
                "pe,pe_ttm,pb,ps,ps_ttm,dv_ratio,dv_ttm,total_share,float_share,"
                "free_share,total_mv,circ_mv"
            ),
        )
    except Exception as exc:
        error_type, message = _classify_tushare_error(exc)
        return ValuationResult(
            success=False,
            symbol=symbol,
            start_date=start_date,
            end_date=end_date,
            provider="tushare",
            market="cn",
            asset_type=asset_type,
            error_type=error_type,
            message=message,
            raw={"raw_error": str(exc)},
        )

    records = _daily_basic_to_records(df, symbol=symbol, asset_type=asset_type)

    if not records:
        return ValuationResult(
            success=False,
            symbol=symbol,
            start_date=start_date,
            end_date=end_date,
            provider="tushare",
            market="cn",
            asset_type=asset_type,
            error_type="empty_data",
            message="No Tushare daily_basic data returned.",
        )

    return ValuationResult(
        success=True,
        symbol=symbol,
        start_date=start_date,
        end_date=end_date,
        provider="tushare",
        market="cn",
        asset_type=asset_type,
        records=records,
    )
