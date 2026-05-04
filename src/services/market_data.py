# 获取股票行情和估值数据
from __future__ import annotations

from pathlib import Path

from src.services.stock_resolver import resolve_stock_code
from src.services.tushare_client import get_tushare_client
from src.storage.cache import load_json_cache, save_json_cache
from src.storage.paths import get_data_cache_dir


def _daily_cache_path(ts_code: str, start_date: str, end_date: str) -> Path:
    filename = f"{ts_code}_{start_date}_{end_date}.json"
    return get_data_cache_dir() / "daily" / filename


def _df_to_records(df, limit: int | None = None) -> list[dict]:
    """
    将 pandas DataFrame 转为适合 JSON 返回的字典列表。
    df 为空时返回空列表；limit 用于限制返回行数。
    缺失值会被替换为空字符串。
    """
    if df is None or df.empty:
        return []

    result_df = df.fillna("")
    if limit is not None:
        result_df = result_df.head(limit)

    return result_df.to_dict(orient="records")

def normalize_tushare_date(value: str) -> str:
    """
    YYYY-MM-DD日期标准化为YYYYMMDD
    """
    normalized = value.strip().replace("-", "").replace("/", "").replace(".", "")

    if len(normalized) != 8 or not normalized.isdigit():
        raise ValueError(f"Invalid date format: {value}. Expected YYYYMMDD or YYYY-MM-DD.")

    return normalized


def get_daily_prices(
    name_or_code: str,
    start_date: str,
    end_date: str,
    limit: int | None = 20,
) -> dict:
    """
    从 Tushare 获取个股日线行情数据。
    输入股票名称或代码、起止日期，可限制返回条数。
    返回包含成功状态、字段列表和行情记录的字典。
    """
    start_date = normalize_tushare_date(start_date)
    end_date = normalize_tushare_date(end_date)

    resolved = resolve_stock_code(name_or_code)
    if not resolved.get("matched"):
        return {
            "success": False,
            "input": name_or_code,
            "message": resolved.get("message"),
            "data": [],
        }

    ts_code = resolved["ts_code"]
    cache_path = _daily_cache_path(ts_code, start_date, end_date)
    cached = load_json_cache(cache_path)
    if cached:
        return {
            "success": True,
            "ts_code": ts_code,
            "name": resolved.get("name"),
            "start_date": start_date,
            "end_date": end_date,
            "count": len(cached),
            "fields": list(cached[0].keys()) if cached else [],
            "data": cached if limit is None else cached[:limit],
            "cache": {
                "hit": True,
                "path": str(cache_path),
            },
        }

    pro = get_tushare_client()

    try:
        df = pro.daily(
            ts_code=ts_code,
            start_date=start_date,
            end_date=end_date,
        )
    except Exception as exc:
        message = str(exc)

        if any(
            pattern in message
            for pattern in [
                "ConnectionError",
                "HTTPConnectionPool",
                "NewConnectionError",
                "Max retries",
                "WinError 10013",
                "访问套接字",
            ]
        ):
            error_type = "network_error"
            user_message = "连接 Tushare daily 接口失败，请检查网络、代理或运行环境权限。"
        elif "频率超限" in message:
            error_type = "rate_limited"
            user_message = "Tushare daily 接口频率超限，请稍后重试或使用缓存。"
        elif "访问权限" in message or "没有接口" in message:
            error_type = "permission_denied"
            user_message = "当前 Tushare token 没有 daily 接口权限，日线行情暂不可用。"
        else:
            error_type = "tushare_error"
            user_message = "调用 Tushare daily 接口失败。"

        return {
            "success": False,
            "error_type": error_type,
            "ts_code": ts_code,
            "start_date": start_date,
            "end_date": end_date,
            "message": user_message,
            "raw_error": message,
            "data": [],
            "cache": {
                "hit": False,
                "path": str(cache_path),
            },
        }

    if df is None or df.empty:
        return {
            "success": False,
            "ts_code": ts_code,
            "start_date": start_date,
            "end_date": end_date,
            "message": "未获取到日线行情数据。",
            "data": [],
        }

    df = df.sort_values("trade_date")
    records = _df_to_records(df, limit=None)
    save_json_cache(cache_path, records)

    return {
        "success": True,
        "ts_code": ts_code,
        "name": resolved.get("name"),
        "start_date": start_date,
        "end_date": end_date,
        "count": len(records),
        "fields": list(df.columns),
        "data": records if limit is None else records[:limit],
        "cache": {
            "hit": False,
            "path": str(cache_path),
        },
    }


    
def get_daily_basic(
    name_or_code: str,
    start_date: str,
    end_date: str,
    limit: int | None = 20,
) -> dict:
    """
    从 Tushare 获取个股每日估值和交易指标。
    输入股票名称或代码、起止日期，可限制返回条数。
    返回市盈率、市净率、市值、换手率等指标数据。
    """
    start_date = normalize_tushare_date(start_date)
    end_date = normalize_tushare_date(end_date)

    resolved = resolve_stock_code(name_or_code)
    if not resolved.get("matched"):
        return {
            "success": False,
            "error_type": "stock_not_found",
            "input": name_or_code,
            "message": resolved.get("message"),
            "data": [],
        }

    ts_code = resolved["ts_code"]
    pro = get_tushare_client()

    try:
        df = pro.daily_basic(
            ts_code=ts_code,
            start_date=start_date,
            end_date=end_date,
            fields=(
                "ts_code,trade_date,close,turnover_rate,volume_ratio,"
                "pe,pe_ttm,pb,ps,ps_ttm,total_mv,circ_mv"
            ),
        )
    except Exception as exc:
        message = str(exc)

        if any(
            pattern in message
            for pattern in [
                "ConnectionError",
                "HTTPConnectionPool",
                "NewConnectionError",
                "Max retries",
                "WinError 10013",
                "访问套接字",
            ]
        ):
            return {
                "success": False,
                "error_type": "network_error",
                "ts_code": ts_code,
                "start_date": start_date,
                "end_date": end_date,
                "message": "连接 Tushare daily_basic 接口失败，请检查网络、代理或运行环境权限。",
                "raw_error": message,
                "data": [],
            }

        if "没有接口" in message or "访问权限" in message:
            return {
                "success": False,
                "error_type": "permission_denied",
                "ts_code": ts_code,
                "start_date": start_date,
                "end_date": end_date,
                "message": "当前 Tushare token 没有 daily_basic 接口权限，估值数据暂不可用。",
                "raw_error": message,
                "data": [],
            }

        if "频率超限" in message:
            return {
                "success": False,
                "error_type": "rate_limited",
                "ts_code": ts_code,
                "start_date": start_date,
                "end_date": end_date,
                "message": "Tushare daily_basic 接口频率超限，请稍后重试或使用缓存。",
                "raw_error": message,
                "data": [],
            }

        return {
            "success": False,
            "error_type": "tushare_error",
            "ts_code": ts_code,
            "start_date": start_date,
            "end_date": end_date,
            "message": "调用 Tushare daily_basic 接口失败。",
            "raw_error": message,
            "data": [],
        }

    if df is None or df.empty:
        return {
            "success": False,
            "error_type": "empty_data",
            "ts_code": ts_code,
            "start_date": start_date,
            "end_date": end_date,
            "message": "未获取到每日估值指标数据。",
            "data": [],
        }

    df = df.sort_values("trade_date")

    return {
        "success": True,
        "ts_code": ts_code,
        "name": resolved.get("name"),
        "start_date": start_date,
        "end_date": end_date,
        "count": len(df),
        "fields": list(df.columns),
        "data": _df_to_records(df, limit=limit),
    }


def get_stock_market_data(
    name_or_code: str,
    start_date: str,
    end_date: str,
    limit: int | None = 20,
) -> dict:
    """
    同时获取个股日线行情和每日估值指标。
    输入股票名称或代码、起止日期，可限制返回条数。
    返回行情数据和估值指标两个结果块。
    """
    start_date = normalize_tushare_date(start_date)
    end_date = normalize_tushare_date(end_date)

    prices = get_daily_prices(name_or_code, start_date, end_date, limit=limit)
    daily_basic = get_daily_basic(name_or_code, start_date, end_date, limit=limit)

    return {
        "success": prices.get("success") or daily_basic.get("success"),
        "input": name_or_code,
        "start_date": start_date,
        "end_date": end_date,
        "prices": prices,
        "daily_basic": daily_basic,
    }
