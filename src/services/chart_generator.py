from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd

from src.services.market_data import get_daily_prices
from src.storage.paths import get_charts_dir

def _records_to_chart_df(records: list[dict]) -> pd.DataFrame:
    """Convert price records to DataFrame for charting."""
    df = pd.DataFrame(records)

    if df.empty:
        return df

    df = df.sort_values("trade_date").reset_index(drop=True)
    df["trade_date"] = pd.to_datetime(df["trade_date"], format="%Y%m%d")

    for column in ["open", "high", "low", "close", "vol", "amount"]:
        if column in df.columns:
            df[column] = pd.to_numeric(df[column], errors="coerce")

    df["ma5"] = df["close"].rolling(5).mean()
    df["ma20"] = df["close"].rolling(20).mean()

    return df

def generate_price_chart(
    name_or_code: str,
    start_date: str,
    end_date: str,
) -> dict:
    """Generate close price chart with MA5 and MA20."""
    prices = get_daily_prices(
        name_or_code=name_or_code,
        start_date=start_date,
        end_date=end_date,
        limit=None,
    )

    if not prices.get("success"):
        return {
            "success": False,
            "error_type": prices.get("error_type", "price_data_unavailable"),
            "message": prices.get("message", "未能获取日线行情数据，无法生成图表。"),
            "source": prices,
        }

    df = _records_to_chart_df(prices["data"])
    if df.empty:
        return {
            "success": False,
            "error_type": "empty_price_data",
            "message": "日线行情数据为空，无法生成图表。",
        }

    ts_code = prices["ts_code"]
    chart_dir = get_charts_dir()
    output_path = chart_dir / f"{ts_code}_{start_date}_{end_date}_price.png"

    plt.figure(figsize=(12, 6))
    plt.plot(df["trade_date"], df["close"], label="Close", linewidth=1.8)
    plt.plot(df["trade_date"], df["ma5"], label="MA5", linestyle="--", linewidth=1.2)
    plt.plot(df["trade_date"], df["ma20"], label="MA20", linestyle="--", linewidth=1.2)

    plt.title(f"{ts_code} Price Trend")
    plt.xlabel("Trade Date")
    plt.ylabel("Price")
    plt.legend()
    plt.grid(alpha=0.3)
    plt.tight_layout()

    plt.savefig(output_path, dpi=150)
    plt.close()

    return {
        "success": True,
        "chart_type": "price",
        "ts_code": ts_code,
        "name": prices.get("name"),
        "start_date": start_date,
        "end_date": end_date,
        "path": str(output_path),
        "relative_path": str(Path("charts") / output_path.name),
        "message": "价格走势图已生成。",
    }

def generate_stock_charts(
    name_or_code: str,
    start_date: str,
    end_date: str,
) -> dict:
    """Generate all currently supported stock charts."""
    price_chart = generate_price_chart(
        name_or_code=name_or_code,
        start_date=start_date,
        end_date=end_date,
    )

    return {
        "success": price_chart.get("success", False),
        "name_or_code": name_or_code,
        "start_date": start_date,
        "end_date": end_date,
        "charts": [price_chart] if price_chart.get("success") else [],
        "errors": [] if price_chart.get("success") else [price_chart],
    }