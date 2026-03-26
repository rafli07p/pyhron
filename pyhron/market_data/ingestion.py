from __future__ import annotations

from dataclasses import dataclass

from pyhron.market_data.cache import MarketDataCache
from pyhron.market_data.client import MarketDataClient
from pyhron.market_data.publisher import MarketDataPublisher


@dataclass
class IngestionResult:
    symbol: str
    success: bool
    cached: bool
    published: bool
    deduplicated: bool = False
    latency_ms: float = 0.0


class MarketDataIngestionService:
    def __init__(
        self,
        client: MarketDataClient,
        cache: MarketDataCache,
        publisher: MarketDataPublisher,
    ) -> None:
        self.client = client
        self.cache = cache
        self.publisher = publisher

    async def ingest_latest(self, symbols: list[str]) -> list[IngestionResult]:
        raise NotImplementedError

    async def shutdown(self) -> None:
        raise NotImplementedError
