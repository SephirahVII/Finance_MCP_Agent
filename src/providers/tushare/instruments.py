from __future__ import annotations

import re

from src.providers.tushare.client import get_client
from src.storage.cache import load_json_cache, save_json_cache
from src.storage.paths import get_data_cache_dir


_CODE_WITH_EXCHANGE_RE = re.compile(r"^\d{6}\.(SH|SZ|BJ)$", re.IGNORECASE)
_CODE_ONLY_RE = re.compile(r"^\d{6}$")


def infer_exchange(code: str) -> str:
    """根据 6 位中国股票代码推断交易所后缀。

    输入：
        code：6 位股票代码，例如 600000、000001、300750。

    输出：
        返回交易所后缀字符串：
        - SH：上海证券交易所
        - SZ：深圳证券交易所
        - BJ：北京证券交易所

    异常：
        如果无法根据代码首位推断交易所，则抛出 ValueError。
    """    
    if code.startswith("6"):
        return "SH"
    if code.startswith(("0", "3")):
        return "SZ"
    if code.startswith(("4", "8", "9")):
        return "BJ"

    raise ValueError(f"Unable to infer exchange from code: {code}")


def normalize_stock_code(name_or_code: str) -> str | None:
    """规范化直接输入的股票代码，不调用 Tushare。

    输入：
        name_or_code：用户输入的股票名称或股票代码。

    输出：
        如果输入已经是标准 ts_code，例如 600000.SH，则直接返回大写后的值。
        如果输入是 6 位股票代码，例如 600000，则补全交易所后缀后返回。
        如果输入不是可识别的股票代码格式，则返回 None。
    """
    value = name_or_code.strip().upper()

    if _CODE_WITH_EXCHANGE_RE.match(value):
        return value

    if _CODE_ONLY_RE.match(value):
        exchange = infer_exchange(value)
        return f"{value}.{exchange}"

    return None


def get_stock_basic() -> list[dict]:
    """Fetch A-share stock basic information from Tushare, with local cache."""
    cache_path = get_data_cache_dir() / "stock_basic.json"

    cached = load_json_cache(cache_path)
    if cached:
        return cached

    pro = get_client()

    try:
        df = pro.stock_basic(
            exchange="",
            list_status="L",
            fields="ts_code,symbol,name,area,industry,list_date,market",
        )
    except Exception as exc:
        fallback = load_json_cache(cache_path)
        if fallback:
            return fallback
        raise exc

    if df is None or df.empty:
        return []

    records = df.fillna("").to_dict(orient="records")
    save_json_cache(cache_path, records)
    return records


def resolve_stock_code(name_or_code: str) -> dict:
    """将股票名称或代码解析为标准 Tushare ts_code。

    输入：
        name_or_code：用户输入的股票名称、股票简称、6 位代码或标准 ts_code。

    输出：
        返回解析结果字典。常见字段包括：
        - matched：是否成功匹配
        - input：原始输入
        - ts_code：匹配到的标准 Tushare 股票代码
        - name：股票名称
        - match_type：匹配方式，例如 code、exact、fuzzy
        - message：解析结果说明
        如果出现多个模糊匹配，还会返回 candidates 候选列表。
    """    
    if not name_or_code or not name_or_code.strip():
        return {
            "matched": False,
            "input": name_or_code,
            "ts_code": None,
            "name": None,
            "message": "Input is empty.",
        }

    normalized = normalize_stock_code(name_or_code)
    if normalized:
        return {
            "matched": True,
            "input": name_or_code,
            "ts_code": normalized,
            "name": None,
            "match_type": "code",
            "message": "Resolved by stock code format.",
        }

    query = name_or_code.strip()
    stocks = get_stock_basic()

    exact_matches = [
        item
        for item in stocks
        if item.get("name") == query or item.get("symbol") == query
    ]

    if len(exact_matches) == 1:
        item = exact_matches[0]
        return {
            "matched": True,
            "input": name_or_code,
            "ts_code": item["ts_code"],
            "name": item["name"],
            "industry": item.get("industry"),
            "area": item.get("area"),
            "market": item.get("market"),
            "list_date": item.get("list_date"),
            "match_type": "exact",
            "message": "Resolved by exact stock name or symbol match.",
        }

    fuzzy_matches = [
        item
        for item in stocks
        if query in item.get("name", "")
    ]

    if len(fuzzy_matches) == 1:
        item = fuzzy_matches[0]
        return {
            "matched": True,
            "input": name_or_code,
            "ts_code": item["ts_code"],
            "name": item["name"],
            "industry": item.get("industry"),
            "area": item.get("area"),
            "market": item.get("market"),
            "list_date": item.get("list_date"),
            "match_type": "fuzzy",
            "message": "Resolved by fuzzy stock name match.",
        }

    if len(fuzzy_matches) > 1:
        return {
            "matched": False,
            "input": name_or_code,
            "ts_code": None,
            "name": None,
            "candidates": fuzzy_matches[:10],
            "message": "Multiple stocks matched. Please provide a more specific name or code.",
        }

    return {
        "matched": False,
        "input": name_or_code,
        "ts_code": None,
        "name": None,
        "message": "No matching stock found.",
    }
