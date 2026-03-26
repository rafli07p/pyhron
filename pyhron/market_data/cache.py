from __future__ import annotations

from pyhron.shared.schemas.tick import TickData


class MarketDataCache:
    def __init__(self, redis_url: str) -> None:
        self.redis_url = redis_url

    async def connect(self) -> None:
        raise NotImplementedError

    async def disconnect(self) -> None:
        raise NotImplementedError

    async def set_latest_tick(self, tick: TickData, ttl_seconds: int = 60) -> None:
        raise NotImplementedError

    async def get_latest_tick(self, symbol: str) -> TickData | None:
        raise NotImplementedError

    async def flush_test_data(self) -> None:
        raise NotImplementedError
