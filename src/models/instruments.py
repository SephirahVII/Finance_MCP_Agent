from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Literal


Market = Literal[
    "cn",
    "hk",
    "us",
    "crypto",
    "global",
    "sg",
    "jp",
    "eu",
    "uk",
    "unknown",
]

AssetType = Literal[
    "stock",
    "index",
    "fund",
    "etf",
    "future",
    "crypto_spot",
    "crypto_future",
    "forex",
    "commodity",
    "unknown",
]


@dataclass(frozen=True)
class Instrument:
    """
    统一的金融标的模型。
    Market表示市场类型，AssetType表示资产类型
    """

    symbol: str
    name: str | None
    market: Market
    asset_type: AssetType
    exchange: str | None = None
    currency: str | None = None
    provider: str | None = None
    raw: dict | None = None

    def to_dict(self) -> dict:
        return asdict(self)
