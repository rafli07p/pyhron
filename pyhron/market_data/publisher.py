from __future__ import annotations

from dataclasses import dataclass

from pyhron.shared.schemas.tick import TickData


@dataclass
class PublishResult:
    success: bool
    partition: int | None
    offset: int | None


class MarketDataPublisher:
    def __init__(self, bootstrap_servers: str, topic: str) -> None:
        self.bootstrap_servers = bootstrap_servers
        self.topic = topic

    async def connect(self) -> None:
        raise NotImplementedError

    async def disconnect(self) -> None:
        raise NotImplementedError

    async def publish_tick(self, tick: TickData) -> PublishResult:
        raise NotImplementedError

    async def publish_batch(self, ticks: list[TickData]) -> list[PublishResult]:
        raise NotImplementedError
