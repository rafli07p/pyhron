"""
Integration tests for market data ingestion.

Tests the full market data pipeline: API connectivity, data parsing,
Kafka publishing, and Redis caching.

Requires:
  - Market data API key (skipped if not configured)
  - Running Kafka and Redis instances (docker-compose)
"""

from __future__ import annotations

import asyncio
import os
from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest
import pytest_asyncio

# TODO: update imports when enthropy.market_data is implemented
# Future paths:
#   MarketDataCache, MarketDataClient, MarketDataIngestionService, MarketDataPublisher — not yet implemented
#   from shared.schemas.market_events import TickEvent (as TickData)
pytest.importorskip("enthropy.market_data.cache", reason="module not yet implemented")
from enthropy.market_data.cache import MarketDataCache
from enthropy.market_data.client import MarketDataClient
from enthropy.market_data.ingestion import MarketDataIngestionService
from enthropy.market_data.publisher import MarketDataPublisher
from enthropy.shared.schemas.tick import TickData

# =============================================================================
# Skip Conditions
# =============================================================================
MARKET_DATA_API_KEY = os.environ.get("MARKET_DATA_API_KEY")
SKIP_NO_API_KEY = pytest.mark.skipif(
    not MARKET_DATA_API_KEY,
    reason="MARKET_DATA_API_KEY not set. Skipping market data integration tests.",
)

REDIS_URL = os.environ.get("REDIS_URL", "redis://localhost:6379/1")
KAFKA_BOOTSTRAP = os.environ.get("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")

SKIP_NO_REDIS = pytest.mark.skipif(
    os.environ.get("SKIP_INTEGRATION", "false").lower() == "true",
    reason="SKIP_INTEGRATION is set. Skipping integration tests.",
)


# =============================================================================
# Fixtures
# =============================================================================
@pytest_asyncio.fixture
async def market_data_client():
    """Market data API client."""
    client = MarketDataClient(
        api_key=MARKET_DATA_API_KEY or "test_key",
        base_url=os.environ.get("MARKET_DATA_BASE_URL", "https://api.marketdata.example.com"),
        timeout=30,
    )
    yield client
    await client.close()


@pytest_asyncio.fixture
async def redis_cache():
    """Redis-backed market data cache."""
    cache = MarketDataCache(redis_url=REDIS_URL)
    await cache.connect()
    yield cache
    await cache.flush_test_data()
    await cache.disconnect()


@pytest_asyncio.fixture
async def kafka_publisher():
    """Kafka market data publisher."""
    publisher = MarketDataPublisher(
        bootstrap_servers=KAFKA_BOOTSTRAP,
        topic="enthropy.market_data.test",
    )
    await publisher.connect()
    yield publisher
    await publisher.disconnect()


@pytest_asyncio.fixture
async def ingestion_service(market_data_client, redis_cache, kafka_publisher):
    """Full market data ingestion service."""
    service = MarketDataIngestionService(
        client=market_data_client,
        cache=redis_cache,
        publisher=kafka_publisher,
    )
    yield service
    await service.shutdown()


# =============================================================================
# Market Data Client Tests
# =============================================================================
class TestMarketDataClient:
    """Tests for direct market data API interaction."""

    @SKIP_NO_API_KEY
    @pytest.mark.asyncio
    async def test_fetch_latest_quote(self, market_data_client: MarketDataClient):
        """Should fetch the latest quote for a valid symbol."""
        tick = await market_data_client.get_latest_quote("BBCA.JK")

        assert tick is not None
        assert isinstance(tick, TickData)
        assert tick.symbol == "BBCA.JK"
        assert tick.price > 0
        assert tick.volume >= 0
        assert tick.bid > 0
        assert tick.ask > 0
        assert tick.ask >= tick.bid

    @SKIP_NO_API_KEY
    @pytest.mark.asyncio
    async def test_fetch_multiple_quotes(self, market_data_client: MarketDataClient):
        """Should fetch quotes for multiple symbols in batch."""
        symbols = ["BBCA.JK", "TLKM.JK", "BMRI.JK", "BBRI.JK"]
        ticks = await market_data_client.get_latest_quotes(symbols)

        assert len(ticks) == len(symbols)
        for tick in ticks:
            assert tick.symbol in symbols
            assert tick.price > 0

    @SKIP_NO_API_KEY
    @pytest.mark.asyncio
    async def test_fetch_historical_data(self, market_data_client: MarketDataClient):
        """Should fetch historical OHLCV data."""
        end_date = datetime.now(UTC)
        start_date = end_date - timedelta(days=30)

        bars = await market_data_client.get_historical_bars(
            symbol="BBCA.JK",
            start=start_date,
            end=end_date,
            interval="1d",
        )

        assert len(bars) > 0
        for bar in bars:
            assert bar.open > 0
            assert bar.high >= bar.low
            assert bar.close > 0
            assert bar.volume >= 0

    @SKIP_NO_API_KEY
    @pytest.mark.asyncio
    async def test_invalid_symbol_returns_none(self, market_data_client: MarketDataClient):
        """Invalid symbol should return None, not raise an error."""
        tick = await market_data_client.get_latest_quote("INVALID_SYMBOL_XYZ")
        assert tick is None

    @SKIP_NO_API_KEY
    @pytest.mark.asyncio
    async def test_rate_limiting_handled(self, market_data_client: MarketDataClient):
        """Client should handle rate limiting gracefully."""
        # Rapid-fire requests to trigger rate limiting
        tasks = [market_data_client.get_latest_quote("BBCA.JK") for _ in range(50)]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # All should succeed (client handles retries internally)
        successful = [r for r in results if isinstance(r, TickData)]
        assert len(successful) == len(results)


# =============================================================================
# Cache Integration Tests
# =============================================================================
class TestMarketDataCache:
    """Tests for Redis market data caching."""

    @SKIP_NO_REDIS
    @pytest.mark.asyncio
    async def test_cache_and_retrieve_tick(self, redis_cache: MarketDataCache):
        """Tick data should be cacheable and retrievable."""
        tick = TickData(
            symbol="BBCA.JK",
            price=Decimal("9250.00"),
            volume=1_500_000,
            bid=Decimal("9245.00"),
            ask=Decimal("9255.00"),
            timestamp=datetime.now(UTC),
            exchange="IDX",
        )

        await redis_cache.set_latest_tick(tick)
        cached = await redis_cache.get_latest_tick("BBCA.JK")

        assert cached is not None
        assert cached.symbol == tick.symbol
        assert cached.price == tick.price

    @SKIP_NO_REDIS
    @pytest.mark.asyncio
    async def test_cache_expiry(self, redis_cache: MarketDataCache):
        """Cached ticks should expire after TTL."""
        tick = TickData(
            symbol="EXPIRY_TEST",
            price=Decimal("100.00"),
            volume=1000,
            bid=Decimal("99.50"),
            ask=Decimal("100.50"),
            timestamp=datetime.now(UTC),
            exchange="TEST",
        )

        await redis_cache.set_latest_tick(tick, ttl_seconds=1)
        # Immediately should be available
        assert await redis_cache.get_latest_tick("EXPIRY_TEST") is not None

        await asyncio.sleep(1.5)
        # After TTL should be gone
        assert await redis_cache.get_latest_tick("EXPIRY_TEST") is None

    @SKIP_NO_REDIS
    @pytest.mark.asyncio
    async def test_cache_multiple_symbols(self, redis_cache: MarketDataCache):
        """Multiple symbols should be cached independently."""
        symbols = ["SYM_A", "SYM_B", "SYM_C"]
        for i, symbol in enumerate(symbols):
            tick = TickData(
                symbol=symbol,
                price=Decimal(str(100 + i * 10)),
                volume=1000 * (i + 1),
                bid=Decimal(str(99 + i * 10)),
                ask=Decimal(str(101 + i * 10)),
                timestamp=datetime.now(UTC),
                exchange="TEST",
            )
            await redis_cache.set_latest_tick(tick)

        for i, symbol in enumerate(symbols):
            cached = await redis_cache.get_latest_tick(symbol)
            assert cached is not None
            assert cached.price == Decimal(str(100 + i * 10))


# =============================================================================
# Kafka Publisher Tests
# =============================================================================
class TestMarketDataPublisher:
    """Tests for Kafka market data publishing."""

    @SKIP_NO_REDIS
    @pytest.mark.asyncio
    async def test_publish_tick(self, kafka_publisher: MarketDataPublisher):
        """Should publish tick data to Kafka topic."""
        tick = TickData(
            symbol="BBCA.JK",
            price=Decimal("9250.00"),
            volume=1_500_000,
            bid=Decimal("9245.00"),
            ask=Decimal("9255.00"),
            timestamp=datetime.now(UTC),
            exchange="IDX",
        )

        result = await kafka_publisher.publish_tick(tick)
        assert result.success is True
        assert result.partition is not None
        assert result.offset is not None

    @SKIP_NO_REDIS
    @pytest.mark.asyncio
    async def test_publish_batch(self, kafka_publisher: MarketDataPublisher):
        """Should publish a batch of ticks efficiently."""
        now = datetime.now(UTC)
        ticks = [
            TickData(
                symbol=f"SYM_{i}",
                price=Decimal(str(100 + i)),
                volume=1000 * i,
                bid=Decimal(str(99 + i)),
                ask=Decimal(str(101 + i)),
                timestamp=now,
                exchange="TEST",
            )
            for i in range(100)
        ]

        results = await kafka_publisher.publish_batch(ticks)
        assert all(r.success for r in results)
        assert len(results) == 100


# =============================================================================
# Full Ingestion Pipeline Tests
# =============================================================================
class TestIngestionPipeline:
    """Tests for the complete market data ingestion pipeline."""

    @SKIP_NO_API_KEY
    @SKIP_NO_REDIS
    @pytest.mark.asyncio
    async def test_full_ingestion_flow(self, ingestion_service: MarketDataIngestionService):
        """Full pipeline: fetch -> validate -> cache -> publish."""
        symbols = ["BBCA.JK", "TLKM.JK"]

        results = await ingestion_service.ingest_latest(symbols)

        assert len(results) == len(symbols)
        for result in results:
            assert result.symbol in symbols
            assert result.cached is True
            assert result.published is True
            assert result.latency_ms < 5000  # Should complete in 5s

    @SKIP_NO_API_KEY
    @SKIP_NO_REDIS
    @pytest.mark.asyncio
    async def test_ingestion_handles_partial_failure(self, ingestion_service: MarketDataIngestionService):
        """Pipeline should handle partial failures gracefully."""
        symbols = ["BBCA.JK", "INVALID_SYMBOL_XYZ", "TLKM.JK"]

        results = await ingestion_service.ingest_latest(symbols)

        successful = [r for r in results if r.success]
        failed = [r for r in results if not r.success]

        assert len(successful) >= 2  # Valid symbols should succeed
        assert len(failed) <= 1  # Invalid symbol may fail

    @SKIP_NO_API_KEY
    @SKIP_NO_REDIS
    @pytest.mark.asyncio
    async def test_ingestion_deduplication(
        self, ingestion_service: MarketDataIngestionService, redis_cache: MarketDataCache
    ):
        """Duplicate ticks should not be re-published."""
        symbols = ["BBCA.JK"]

        # First ingestion
        await ingestion_service.ingest_latest(symbols)
        first_tick = await redis_cache.get_latest_tick("BBCA.JK")

        # Second ingestion (same data)
        results = await ingestion_service.ingest_latest(symbols)

        # If price hasn't changed, should be deduplicated
        second_tick = await redis_cache.get_latest_tick("BBCA.JK")
        if first_tick and second_tick and first_tick.price == second_tick.price:
            assert results[0].deduplicated is True
