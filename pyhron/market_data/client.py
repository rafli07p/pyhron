from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal

from pyhron.shared.schemas.tick import TickData


@dataclass
class OHLCVBar:
    date: date
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    volume: int


class MarketDataClient:
    def __init__(self, api_key: str, base_url: str, timeout: int = 30) -> None:
        self.api_key = api_key
        self.base_url = base_url
        self.timeout = timeout

    async def get_latest_quote(self, symbol: str) -> TickData | None:
        raise NotImplementedError

    async def get_latest_quotes(self, symbols: list[str]) -> list[TickData]:
        raise NotImplementedError

    async def get_historical_bars(
        self, symbol: str, start: datetime, end: datetime, interval: str
    ) -> list[OHLCVBar]:
        raise NotImplementedError

    async def close(self) -> None:
        raise NotImplementedError
