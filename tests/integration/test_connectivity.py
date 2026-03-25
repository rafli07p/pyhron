"""Integration tests for service connectivity.

Verifies that all infrastructure services (PostgreSQL, Redis, Kafka)
and the API gateway are reachable from the test runner. These tests
require a running ``docker compose up`` environment.

Run with::

    pytest tests/integration/test_connectivity.py -m integration
"""

from __future__ import annotations

import os

import pytest

# ---------------------------------------------------------------------------
# Defaults match docker-compose.yaml development values
# ---------------------------------------------------------------------------
API_BASE = os.environ.get("API_BASE_URL", "http://localhost:8000")
DATABASE_URL = os.environ.get(
    "DATABASE_URL",
    "postgresql+asyncpg://pyhron:pyhron_dev@localhost:5432/pyhron",
)
REDIS_URL = os.environ.get("REDIS_URL", "redis://:pyhron_dev@localhost:6379/0")
KAFKA_BOOTSTRAP = os.environ.get("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")

pytestmark = pytest.mark.integration


# ---------------------------------------------------------------------------
# API Gateway
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_api_health() -> None:
    """API /health endpoint returns 200 with status ok."""
    import httpx

    async with httpx.AsyncClient(base_url=API_BASE, timeout=10.0) as client:
        resp = await client.get("/health")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ok"
    assert "version" in body
    assert "timestamp" in body


@pytest.mark.asyncio
async def test_api_openapi_docs() -> None:
    """OpenAPI spec is served at /openapi.json."""
    import httpx

    async with httpx.AsyncClient(base_url=API_BASE, timeout=10.0) as client:
        resp = await client.get("/openapi.json")
    assert resp.status_code == 200
    spec = resp.json()
    assert spec["info"]["title"] == "Pyhron Trading Platform API"


# ---------------------------------------------------------------------------
# PostgreSQL (TimescaleDB)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_postgres_connection() -> None:
    """Can connect to PostgreSQL and execute a simple query."""
    from sqlalchemy import text
    from sqlalchemy.ext.asyncio import create_async_engine

    engine = create_async_engine(DATABASE_URL, echo=False)
    try:
        async with engine.begin() as conn:
            result = await conn.execute(text("SELECT 1 AS ping"))
            row = result.fetchone()
            assert row is not None
            assert row[0] == 1
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_postgres_timescaledb_extension() -> None:
    """TimescaleDB extension is available in PostgreSQL."""
    from sqlalchemy import text
    from sqlalchemy.ext.asyncio import create_async_engine

    engine = create_async_engine(DATABASE_URL, echo=False)
    try:
        async with engine.begin() as conn:
            result = await conn.execute(
                text("SELECT extname FROM pg_available_extensions WHERE extname = 'timescaledb'")
            )
            row = result.fetchone()
            assert row is not None, "TimescaleDB extension not available"
    finally:
        await engine.dispose()


# ---------------------------------------------------------------------------
# Redis
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_redis_ping() -> None:
    """Redis responds to PING."""
    from redis.asyncio import from_url as redis_from_url

    client = redis_from_url(REDIS_URL, decode_responses=True)
    try:
        pong = await client.ping()
        assert pong is True
    finally:
        await client.aclose()


@pytest.mark.asyncio
async def test_redis_set_get() -> None:
    """Redis can store and retrieve a value."""
    from redis.asyncio import from_url as redis_from_url

    client = redis_from_url(REDIS_URL, decode_responses=True)
    try:
        await client.set("pyhron:test:connectivity", "ok", ex=30)
        value = await client.get("pyhron:test:connectivity")
        assert value == "ok"
        await client.delete("pyhron:test:connectivity")
    finally:
        await client.aclose()


# ---------------------------------------------------------------------------
# Kafka
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_kafka_broker_reachable() -> None:
    """Kafka broker accepts connections and responds to metadata requests."""
    from aiokafka import AIOKafkaProducer

    producer = AIOKafkaProducer(
        bootstrap_servers=KAFKA_BOOTSTRAP,
        request_timeout_ms=10000,
    )
    try:
        await producer.start()
        # If start() succeeds, the broker is reachable and metadata was fetched
        assert producer.client is not None
    finally:
        await producer.stop()


@pytest.mark.asyncio
async def test_kafka_produce_consume() -> None:
    """Kafka can produce and consume a message on a test topic."""
    import json

    from aiokafka import AIOKafkaConsumer, AIOKafkaProducer

    topic = "pyhron-test-connectivity"
    test_msg = {"test": "connectivity", "status": "ok"}

    # Produce
    producer = AIOKafkaProducer(
        bootstrap_servers=KAFKA_BOOTSTRAP,
        request_timeout_ms=10000,
    )
    await producer.start()
    try:
        await producer.send_and_wait(
            topic,
            json.dumps(test_msg).encode(),
        )
    finally:
        await producer.stop()

    # Consume
    consumer = AIOKafkaConsumer(
        topic,
        bootstrap_servers=KAFKA_BOOTSTRAP,
        auto_offset_reset="earliest",
        group_id="pyhron-test-connectivity-group",
        consumer_timeout_ms=10000,
    )
    await consumer.start()
    try:
        msg = await consumer.getone()
        payload = json.loads(msg.value.decode())
        assert payload["test"] == "connectivity"
        assert payload["status"] == "ok"
    finally:
        await consumer.stop()
