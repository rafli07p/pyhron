"""Market data ingestion orchestrator for the Pyhron trading platform.

Coordinates fetch -> cache -> publish pipeline for real-time market data.
Handles deduplication and latency tracking per symbol.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass

from pyhron.market_data.cache import MarketDataCache
from pyhron.market_data.client import MarketDataClient
from pyhron.market_data.publisher import MarketDataPublisher

logger = logging.getLogger(__name__)


@dataclass
class IngestionResult:
    symbol: str
    success: bool
    cached: bool
    published: bool
    deduplicated: bool = False
    latency_ms: float = 0.0


class MarketDataIngestionService:
    """Orchestrates the market data pipeline: fetch -> cache -> publish.

    Parameters
    ----------
    client:
        Market data client for fetching quotes.
    cache:
        Redis cache for latest tick storage.
    publisher:
        Kafka publisher for distributing ticks.
    dedup_window_ms:
        Minimum interval between publishes for the same symbol (ms).
        Ticks arriving within this window are deduplicated.
    """

    def __init__(
        self,
        client: MarketDataClient,
        cache: MarketDataCache,
        publisher: MarketDataPublisher,
        dedup_window_ms: int = 500,
    ) -> None:
        self.client = client
        self.cache = cache
        self.publisher = publisher
        self._dedup_window_ms = dedup_window_ms
        self._last_publish: dict[str, float] = {}

    async def ingest_latest(self, symbols: list[str]) -> list[IngestionResult]:
        """Fetch, cache, and publish latest quotes for the given symbols.

        For each symbol:
        1. Fetch the latest quote from the data provider.
        2. Cache the tick in Redis (with 60s TTL).
        3. Publish to Kafka (if not deduplicated).

        Returns a result per symbol indicating what happened.
        """
        results: list[IngestionResult] = []

        ticks = await self.client.get_latest_quotes(symbols)
        fetched_symbols = {t.symbol for t in ticks}

        # Report failures for symbols that didn't return a tick
        for symbol in symbols:
            if symbol not in fetched_symbols:
                results.append(IngestionResult(
                    symbol=symbol, success=False, cached=False, published=False,
                ))

        for tick in ticks:
            t0 = time.monotonic()
            cached = False
            published = False
            deduplicated = False

            # Cache
            try:
                await self.cache.set_latest_tick(tick, ttl_seconds=60)
                cached = True
            except Exception:
                logger.exception("ingestion.cache_failed", extra={"symbol": tick.symbol})

            # Dedup check
            now_ms = time.monotonic() * 1000
            last = self._last_publish.get(tick.symbol, 0)
            if (now_ms - last) < self._dedup_window_ms:
                deduplicated = True
            else:
                # Publish
                try:
                    pub_result = await self.publisher.publish_tick(tick)
                    published = pub_result.success
                    if published:
                        self._last_publish[tick.symbol] = now_ms
                except Exception:
                    logger.exception("ingestion.publish_failed", extra={"symbol": tick.symbol})

            latency_ms = (time.monotonic() - t0) * 1000

            results.append(IngestionResult(
                symbol=tick.symbol,
                success=cached or published,
                cached=cached,
                published=published,
                deduplicated=deduplicated,
                latency_ms=round(latency_ms, 2),
            ))

        return results

    async def shutdown(self) -> None:
        """Gracefully shut down all components."""
        await self.client.close()
        await self.cache.disconnect()
        await self.publisher.disconnect()
        logger.info("ingestion_service.shutdown")
