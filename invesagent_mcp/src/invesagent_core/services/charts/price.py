from __future__ import annotations

from pathlib import Path
from typing import Iterable

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
import pandas as pd

from invesagent_core.models.market_data import MarketDataResult, OHLCVRecord
from invesagent_core.services.data.market_data import get_ohlcv
from invesagent_core.services.metrics.technical import (
    calc_bollinger_bands,
    calc_kdj,
    calc_macd,
    calc_moving_average,
    calc_rsi,
    parse_indicators,
    parse_windows,
)
from invesagent_core.storage.paths import get_charts_dir


def _records_to_chart_df(records: list[OHLCVRecord]) -> pd.DataFrame:
    """Convert unified OHLCV records to a chart DataFrame."""
    data = [record.to_dict() for record in records]
    df = pd.DataFrame(data)

    if df.empty:
        return df

    df = df.sort_values("trade_time").reset_index(drop=True)
    df["trade_time"] = pd.to_datetime(df["trade_time"], errors="coerce")

    for column in ["open", "high", "low", "close", "volume", "amount"]:
        if column in df.columns:
            df[column] = pd.to_numeric(df[column], errors="coerce")

    return df


def _safe_chart_value(value) -> float | None:
    if pd.isna(value):
        return None
    return float(value)


def _x_values(df: pd.DataFrame, chart_type: str):
    if chart_type == "line":
        return df["trade_time"]
    return range(len(df))


def _plot_candles(ax, df: pd.DataFrame) -> None:
    """Draw a lightweight candlestick chart without extra dependencies."""
    x_values = range(len(df))
    width = 0.6

    for x, item in zip(x_values, df.to_dict(orient="records")):
        open_price = _safe_chart_value(item.get("open"))
        high_price = _safe_chart_value(item.get("high"))
        low_price = _safe_chart_value(item.get("low"))
        close_price = _safe_chart_value(item.get("close"))

        if None in (open_price, high_price, low_price, close_price):
            continue

        color = "#d62728" if close_price >= open_price else "#2ca02c"
        body_low = min(open_price, close_price)
        body_height = abs(close_price - open_price) or 0.01

        ax.vlines(x, low_price, high_price, color=color, linewidth=1)
        ax.add_patch(
            Rectangle(
                (x - width / 2, body_low),
                width,
                body_height,
                facecolor=color,
                edgecolor=color,
                alpha=0.75,
            )
        )

    _set_candlestick_xticks(ax, df)


def _set_candlestick_xticks(ax, df: pd.DataFrame) -> None:
    step = max(len(df) // 8, 1)
    ticks = list(range(0, len(df), step))
    labels = []
    for index in ticks:
        value = df.iloc[index]["trade_time"]
        labels.append(str(value)[:10] if pd.isna(value) else value.strftime("%Y-%m-%d"))
    ax.set_xticks(ticks)
    ax.set_xticklabels(labels, rotation=30, ha="right")


def _build_chart_filename(
    market_data: MarketDataResult,
    chart_type: str,
    ma_windows: list[int],
    show_volume: bool,
    indicators: list[str],
) -> str:
    safe_symbol = market_data.symbol.replace("/", "_").replace(":", "_")
    ma_part = "ma-" + "-".join(str(window) for window in ma_windows) if ma_windows else "no-ma"
    volume_part = "volume" if show_volume else "no-volume"
    indicator_part = "-".join(indicators) if indicators else "no-indicator"

    return (
        f"{safe_symbol}_{market_data.market}_{market_data.asset_type}_"
        f"{market_data.start_date}_{market_data.end_date}_"
        f"ohlcv_{chart_type}_{ma_part}_{volume_part}_{indicator_part}.png"
    )


def _format_provider_name(provider: str | None) -> str:
    if not provider:
        return "provider"

    names = {
        "akshare": "AKShare",
        "tushare": "Tushare",
        "binance": "Binance",
    }

    return names.get(provider.lower(), provider)


def _prepare_chart_indicators(
    df: pd.DataFrame,
    selected_indicators: list[str],
    boll_window: int,
    boll_std: float,
    rsi_window: int,
    macd_fast: int,
    macd_slow: int,
    macd_signal: int,
    kdj_window: int,
) -> pd.DataFrame:
    """Add requested technical indicator columns to a chart DataFrame."""
    result = df.copy()

    if "bollinger" in selected_indicators:
        boll = calc_bollinger_bands(result["close"], window=boll_window, num_std=boll_std)
        result = pd.concat([result, boll], axis=1)

    if "rsi" in selected_indicators:
        result["rsi"] = calc_rsi(result["close"], window=rsi_window)

    if "macd" in selected_indicators:
        macd = calc_macd(
            result["close"],
            fast=macd_fast,
            slow=macd_slow,
            signal=macd_signal,
        )
        result = pd.concat([result, macd], axis=1)

    if "kdj" in selected_indicators:
        kdj = calc_kdj(result["high"], result["low"], result["close"], window=kdj_window)
        result = pd.concat([result, kdj], axis=1)

    return result


def generate_ohlcv_price_chart_from_result(
    market_data: MarketDataResult,
    chart_type: str = "line",
    ma_windows: Iterable[int] | str | None = "5,20,60",
    show_volume: bool = False,
    indicators: Iterable[str] | str | None = "",
    boll_window: int = 20,
    boll_std: float = 2.0,
    rsi_window: int = 14,
    macd_fast: int = 12,
    macd_slow: int = 26,
    macd_signal: int = 9,
    kdj_window: int = 9,
) -> dict:
    """Generate price chart from unified MarketDataResult."""
    if not market_data.success:
        return {
            "success": False,
            "error_type": market_data.error_type,
            "message": market_data.message or "Market data is unavailable.",
            "source": market_data.to_dict(),
        }

    df = _records_to_chart_df(market_data.records)

    if df.empty:
        return {
            "success": False,
            "error_type": "empty_market_data",
            "message": "No OHLCV records available for chart generation.",
            "source": market_data.to_dict(),
        }

    normalized_chart_type = chart_type.strip().lower()

    if normalized_chart_type not in ("line", "candlestick"):
        return {
            "success": False,
            "error_type": "unsupported_chart_type",
            "message": "chart_type must be 'line' or 'candlestick'.",
            "chart_type": chart_type,
        }

    windows = parse_windows(ma_windows, default=[5, 20, 60])
    selected_indicators = parse_indicators(indicators)
    supported_indicators = {"bollinger", "rsi", "macd", "kdj"}
    unsupported_indicators = [
        indicator for indicator in selected_indicators if indicator not in supported_indicators
    ]

    if unsupported_indicators:
        return {
            "success": False,
            "error_type": "unsupported_indicator",
            "message": (
                "Supported indicators are: bollinger, rsi, macd, kdj. "
                f"Unsupported: {unsupported_indicators}"
            ),
            "indicators": selected_indicators,
        }

    for window in windows:
        df[f"ma{window}"] = calc_moving_average(df["close"], window)

    df = _prepare_chart_indicators(
        df=df,
        selected_indicators=selected_indicators,
        boll_window=boll_window,
        boll_std=boll_std,
        rsi_window=rsi_window,
        macd_fast=macd_fast,
        macd_slow=macd_slow,
        macd_signal=macd_signal,
        kdj_window=kdj_window,
    )

    chart_dir = get_charts_dir()
    output_path = chart_dir / _build_chart_filename(
        market_data=market_data,
        chart_type=normalized_chart_type,
        ma_windows=windows,
        show_volume=show_volume,
        indicators=selected_indicators,
    )

    panel_names: list[str] = []
    if show_volume:
        panel_names.append("volume")
    for indicator in ("rsi", "macd", "kdj"):
        if indicator in selected_indicators:
            panel_names.append(indicator)

    axes_count = 1 + len(panel_names)
    fig, axes = plt.subplots(
        axes_count,
        1,
        figsize=(12, 6 + 1.8 * len(panel_names)),
        sharex=normalized_chart_type == "line",
        gridspec_kw={"height_ratios": [3] + [1] * len(panel_names)},
    )

    if axes_count == 1:
        price_ax = axes
        panel_axes = {}
    else:
        price_ax = axes[0]
        panel_axes = {name: ax for name, ax in zip(panel_names, axes[1:])}

    if normalized_chart_type == "line":
        price_ax.plot(df["trade_time"], df["close"], label="Close", linewidth=1.8)
    else:
        _plot_candles(price_ax, df)

    for window in windows:
        column = f"ma{window}"
        if column not in df.columns or not df[column].notna().any():
            continue

        if normalized_chart_type == "line":
            price_ax.plot(
                df["trade_time"],
                df[column],
                label=f"MA{window}",
                linestyle="--",
                linewidth=1.2,
            )
        else:
            price_ax.plot(
                range(len(df)),
                df[column],
                label=f"MA{window}",
                linestyle="--",
                linewidth=1.2,
            )

    x_values = _x_values(df, normalized_chart_type)
    if "bollinger" in selected_indicators and df["boll_upper"].notna().any():
        price_ax.plot(x_values, df["boll_upper"], label=f"BOLL Upper({boll_window})", linewidth=1)
        price_ax.plot(x_values, df["boll_middle"], label=f"BOLL Mid({boll_window})", linewidth=1)
        price_ax.plot(x_values, df["boll_lower"], label=f"BOLL Lower({boll_window})", linewidth=1)
        price_ax.fill_between(
            x_values,
            df["boll_lower"].astype(float),
            df["boll_upper"].astype(float),
            alpha=0.08,
        )

    price_ax.set_title(
        f"{market_data.symbol} {normalized_chart_type.title()} Chart ({market_data.provider})"
    )
    price_ax.set_ylabel("Price")
    price_ax.legend()
    price_ax.grid(alpha=0.3)

    if normalized_chart_type == "line":
        price_ax.set_xlabel("Trade Time")

    if "volume" in panel_axes:
        volume_ax = panel_axes["volume"]
        volume_values = df["volume"] if "volume" in df.columns else pd.Series([0] * len(df))

        if normalized_chart_type == "line":
            volume_ax.bar(df["trade_time"], volume_values, color="#4c78a8", alpha=0.45)
        else:
            volume_ax.bar(range(len(df)), volume_values, color="#4c78a8", alpha=0.45)
            _set_candlestick_xticks(volume_ax, df)

        volume_ax.set_ylabel("Volume")
        volume_ax.grid(alpha=0.2)

    if "rsi" in panel_axes:
        rsi_ax = panel_axes["rsi"]
        rsi_ax.plot(x_values, df["rsi"], label=f"RSI({rsi_window})", color="#9467bd", linewidth=1.2)
        rsi_ax.axhline(70, color="#d62728", linestyle="--", linewidth=0.8, alpha=0.6)
        rsi_ax.axhline(30, color="#2ca02c", linestyle="--", linewidth=0.8, alpha=0.6)
        rsi_ax.set_ylabel("RSI")
        rsi_ax.set_ylim(0, 100)
        rsi_ax.legend(loc="upper left")
        rsi_ax.grid(alpha=0.2)

    if "macd" in panel_axes:
        macd_ax = panel_axes["macd"]
        macd_ax.bar(x_values, df["macd_hist"], color="#4c78a8", alpha=0.45, label="MACD Hist")
        macd_ax.plot(x_values, df["macd_dif"], label=f"DIF({macd_fast})", linewidth=1.1)
        macd_ax.plot(x_values, df["macd_dea"], label=f"DEA({macd_signal})", linewidth=1.1)
        macd_ax.axhline(0, color="#555555", linewidth=0.8, alpha=0.6)
        macd_ax.set_ylabel("MACD")
        macd_ax.legend(loc="upper left")
        macd_ax.grid(alpha=0.2)

    if "kdj" in panel_axes:
        kdj_ax = panel_axes["kdj"]
        kdj_ax.plot(x_values, df["kdj_k"], label="K", linewidth=1.1)
        kdj_ax.plot(x_values, df["kdj_d"], label="D", linewidth=1.1)
        kdj_ax.plot(x_values, df["kdj_j"], label="J", linewidth=1.1)
        kdj_ax.set_ylabel("KDJ")
        kdj_ax.legend(loc="upper left")
        kdj_ax.grid(alpha=0.2)

    fig.tight_layout()
    fig.savefig(output_path, dpi=150)
    plt.close(fig)

    return {
        "success": True,
        "chart_type": normalized_chart_type,
        "symbol": market_data.symbol,
        "market": market_data.market,
        "asset_type": market_data.asset_type,
        "provider": market_data.provider,
        "start_date": market_data.start_date,
        "end_date": market_data.end_date,
        "ma_windows": windows,
        "show_volume": show_volume,
        "indicators": selected_indicators,
        "path": str(output_path),
        "relative_path": str(Path("charts") / output_path.name),
        "message": f"\u5df2\u57fa\u4e8e{_format_provider_name(market_data.provider)} \u7684 OHLCV \u884c\u60c5\u6570\u636e\u751f\u6210\u4ef7\u683c\u56fe\u3002",
    }


def generate_ohlcv_price_chart(
    symbol: str,
    market: str,
    start_date: str,
    end_date: str,
    asset_type: str = "stock",
    provider: str = "auto",
    chart_type: str = "line",
    ma_windows: Iterable[int] | str | None = "5,20,60",
    show_volume: bool = False,
    indicators: Iterable[str] | str | None = "",
    boll_window: int = 20,
    boll_std: float = 2.0,
    rsi_window: int = 14,
    macd_fast: int = 12,
    macd_slow: int = 26,
    macd_signal: int = 9,
    kdj_window: int = 9,
    frequency: str = "daily",
    adjust: str | None = None,
) -> dict:
    """Fetch unified OHLCV data and generate a price chart."""
    market_data = get_ohlcv(
        symbol=symbol,
        market=market,
        asset_type=asset_type,
        start_date=start_date,
        end_date=end_date,
        provider=provider,
        frequency=frequency,
        adjust=adjust,
    )

    return generate_ohlcv_price_chart_from_result(
        market_data,
        chart_type=chart_type,
        ma_windows=ma_windows,
        show_volume=show_volume,
        indicators=indicators,
        boll_window=boll_window,
        boll_std=boll_std,
        rsi_window=rsi_window,
        macd_fast=macd_fast,
        macd_slow=macd_slow,
        macd_signal=macd_signal,
        kdj_window=kdj_window,
    )
