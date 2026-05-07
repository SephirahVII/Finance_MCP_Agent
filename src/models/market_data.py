from __future__ import annotations

from dataclasses import asdict, dataclass, field

@dataclass(frozen=True)
class OHLCVRecord:
    """
    统一的 OHLCV 行情记录模型。
    该模型描述某个金融标的在一个交易时间点或周期内的一根行情数据。
    """

    symbol: str
    trade_time: str
    open: float
    high: float
    low: float
    close: float
    volume: float | None = None
    amount: float | None = None
    provider: str | None = None
    market: str | None = None
    asset_type: str | None = None
    raw: dict | None = None

    def to_dict(self) -> dict:
        return asdict(self)

@dataclass(frozen=True)
class MarketDataResult:
    """
    统一的行情数据查询结果模型。
    该模型用于描述一次行情请求是否成功，以及返回的数据、提示和原始信息。
    """

    success: bool
    symbol: str
    start_date: str
    end_date: str
    provider: str
    market: str
    asset_type: str
    records: list[OHLCVRecord] = field(default_factory=list)
    error_type: str | None = None
    message: str | None = None
    warnings: list[str] = field(default_factory=list)
    raw: dict | None = None

    def to_dict(self) -> dict:
        data = asdict(self)
        data["records"] = [record.to_dict() for record in self.records]
        return data
