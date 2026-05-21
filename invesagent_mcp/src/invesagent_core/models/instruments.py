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
    缁熶竴鐨勯噾铻嶆爣鐨勬ā鍨嬨�?
    Market琛ㄧず甯傚満绫诲瀷锛孉ssetType琛ㄧず璧勪骇绫诲瀷
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
