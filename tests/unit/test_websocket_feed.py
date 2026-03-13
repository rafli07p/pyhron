"""Unit tests for the Pyhron WebSocket real-time feed.

Tests connection manager, message routing, rate limiting, market status,
and Kafka-Redis bridge transformation logic.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch
from zoneinfo import ZoneInfo

import pytest

# The websocket_gateway __init__.py imports jwt/cryptography which may
# not be available in all CI environments (e.g. missing _cffi_backend).
try:
    from services.api.websocket_gateway.connection_manager import (
        WebSocketConnectionManager,
    )
    from services.api.websocket_gateway.kafka_redis_bridge import (
        KafkaRedisBridge,
        MessageRouter,
    )
    from services.api.websocket_gateway.market_status_broadcaster import (
        MarketStatusBroadcaster,
    )
    from services.api.websocket_gateway.ws_rate_limiter import WebSocketRateLimiter
except BaseException:
    pytest.skip(
        "WebSocket gateway dependencies unavailable (jwt/cryptography)",
        allow_module_level=True,
    )

from shared.kafka_topics import KafkaTopic

# ── Helpers ──────────────────────────────────────────────────────────────


class MockWebSocket:
    """Minimal WebSocket mock for testing the connection manager."""

    def __init__(self) -> None:
        self.accepted = False
        self.closed = False
        self.close_code: int | None = None
        self.sent_messages: list[dict[str, Any]] = []

    async def accept(self) -> None:
        self.accepted = True

    async def close(self, code: int = 1000, reason: str = "") -> None:
        self.closed = True
        self.close_code = code

    async def send_json(self, data: dict[str, Any]) -> None:
        self.sent_messages.append(data)


def _mock_redis() -> MagicMock:
    """Create a mock Redis client."""
    redis = MagicMock()
    redis.publish = AsyncMock(return_value=1)
    redis.setex = AsyncMock()
    redis.get = AsyncMock(return_value=None)
    redis.pipeline = MagicMock()
    pipe = MagicMock()
    pipe.delete = MagicMock(return_value=pipe)
    pipe.execute = AsyncMock(return_value=[])
    redis.pipeline.return_value = pipe
    return redis


def _valid_jwt_payload() -> MagicMock:
    """Return a mock TokenPayload for successful auth."""
    payload = MagicMock()
    payload.sub = "user-001"
    payload.tenant_id = "tenant-abc"
    payload.role = "TRADER"
    return payload


# ── Test 1: Connection registered on connect ─────────────────────────────


async def test_connection_registered_on_connect() -> None:
    manager = WebSocketConnectionManager(_mock_redis())
    ws = MockWebSocket()
    await manager.connect(ws, "conn-001")  # type: ignore[arg-type]
    assert manager.is_connected("conn-001")


# ── Test 2: Unauthenticated connection cannot subscribe ──────────────────


async def test_unauthenticated_cannot_subscribe() -> None:
    manager = WebSocketConnectionManager(_mock_redis())
    ws = MockWebSocket()
    await manager.connect(ws, "conn-001")  # type: ignore[arg-type]
    result = await manager.subscribe("conn-001", "quotes", "BBCA")
    assert result is False


# ── Test 3: Valid JWT authenticates connection ───────────────────────────


async def test_valid_jwt_authenticates() -> None:
    manager = WebSocketConnectionManager(_mock_redis())
    ws = MockWebSocket()
    await manager.connect(ws, "conn-001")  # type: ignore[arg-type]

    with patch(
        "services.api.websocket_gateway.connection_manager.verify_token",
        return_value=_valid_jwt_payload(),
    ):
        user = await manager.authenticate("conn-001", "valid.jwt.token")

    assert user is not None
    assert user.user_id == "user-001"
    assert manager.is_authenticated("conn-001")


# ── Test 4: Expired JWT fails authentication ─────────────────────────────


async def test_expired_jwt_fails() -> None:
    manager = WebSocketConnectionManager(_mock_redis())
    ws = MockWebSocket()
    await manager.connect(ws, "conn-001")  # type: ignore[arg-type]

    with patch(
        "services.api.websocket_gateway.connection_manager.verify_token",
        side_effect=Exception("token_expired"),
    ):
        user = await manager.authenticate("conn-001", "expired.jwt.token")

    assert user is None
    assert not manager.is_authenticated("conn-001")


# ── Test 5: Message router maps topics to correct channels ───────────────


def test_router_maps_ohlcv_to_quotes_channel() -> None:
    router = MessageRouter()
    payload: dict[str, str] = {"symbol": "BBCA", "close": "9250"}
    channel = router.route(KafkaTopic.VALIDATED_EOD_OHLCV, payload)
    assert channel == "pyhron:quotes:BBCA"


def test_router_maps_order_filled_to_user_channel() -> None:
    router = MessageRouter()
    payload: dict[str, str] = {"user_id": "user-123", "order_id": "ord-456"}
    channel = router.route(KafkaTopic.ORDER_FILLED, payload)
    assert channel == "pyhron:orders:user-123"


def test_router_maps_position_updated_to_user_channel() -> None:
    router = MessageRouter()
    payload: dict[str, str] = {"user_id": "user-789"}
    channel = router.route(KafkaTopic.POSITION_UPDATED, payload)
    assert channel == "pyhron:positions:user-789"


def test_router_maps_signals_to_strategy_channel() -> None:
    router = MessageRouter()
    payload: dict[str, str] = {"strategy_id": "strat-100"}
    channel = router.route(KafkaTopic.MOMENTUM_SIGNALS, payload)
    assert channel == "pyhron:signals:strat-100"


# ── Test 6: Rate limiter allows up to limit then blocks ──────────────────


async def test_rate_limiter_blocks_at_limit() -> None:
    mock_redis = _mock_redis()

    # Simulate Lua script: return incrementing count
    call_count = 0

    async def script_side_effect(keys: list[str], args: list[int]) -> int:
        nonlocal call_count
        call_count += 1
        return call_count

    mock_script = AsyncMock(side_effect=script_side_effect)
    mock_redis.register_script = MagicMock(return_value=mock_script)

    limiter = WebSocketRateLimiter(mock_redis)

    # First 100 calls should be allowed (count <= 100)
    for _ in range(100):
        result = await limiter.check_inbound("conn-001")
        assert result is True

    # 101st call: count=101 > 100
    result = await limiter.check_inbound("conn-001")
    assert result is False


# ── Test 7: Max connections per user enforced ────────────────────────────


async def test_max_connections_per_user_enforced() -> None:
    manager = WebSocketConnectionManager(_mock_redis())
    user_id = "user-abc"

    mock_payload = MagicMock()
    mock_payload.sub = user_id
    mock_payload.tenant_id = "tenant-1"
    mock_payload.role = "TRADER"

    with patch(
        "services.api.websocket_gateway.connection_manager.verify_token",
        return_value=mock_payload,
    ):
        # Connect and authenticate 5 connections (the max)
        for i in range(5):
            ws = MockWebSocket()
            await manager.connect(ws, f"conn-{i:03d}")  # type: ignore[arg-type]
            result = await manager.authenticate(f"conn-{i:03d}", "jwt")
            assert result is not None

        # 6th connection: authenticate should return None
        ws6 = MockWebSocket()
        await manager.connect(ws6, "conn-005")  # type: ignore[arg-type]
        result = await manager.authenticate("conn-005", "jwt")
        assert result is None


# ── Test 8: Disconnect cleans up subscriptions ───────────────────────────


async def test_disconnect_removes_subscriptions() -> None:
    manager = WebSocketConnectionManager(_mock_redis())
    ws = MockWebSocket()
    await manager.connect(ws, "conn-001")  # type: ignore[arg-type]

    with patch(
        "services.api.websocket_gateway.connection_manager.verify_token",
        return_value=_valid_jwt_payload(),
    ):
        await manager.authenticate("conn-001", "jwt")

    await manager.subscribe("conn-001", "quotes", "BBCA")
    assert manager.is_connected("conn-001")

    await manager.disconnect("conn-001")
    assert not manager.is_connected("conn-001")

    # Broadcasting should reach 0 connections
    count = await manager.broadcast_to_channel("pyhron:quotes:BBCA", {"type": "QUOTE_UPDATE"})
    assert count == 0


# ── Test 9: Market status returns correct session ────────────────────────


def test_market_status_session1() -> None:
    broadcaster = MarketStatusBroadcaster()
    wib = ZoneInfo("Asia/Jakarta")
    now = datetime(2025, 3, 3, 10, 30, 0, tzinfo=wib)

    with patch(
        "strategy_engine.idx_trading_calendar.is_trading_day",
        return_value=True,
    ):
        status = broadcaster.get_current_status(now)

    assert status.status == "OPEN"
    assert status.session == "SESSION_1"


def test_market_status_intermission() -> None:
    broadcaster = MarketStatusBroadcaster()
    wib = ZoneInfo("Asia/Jakarta")
    now = datetime(2025, 3, 3, 12, 30, 0, tzinfo=wib)

    with patch(
        "strategy_engine.idx_trading_calendar.is_trading_day",
        return_value=True,
    ):
        status = broadcaster.get_current_status(now)

    assert status.status == "CLOSED"
    assert status.session == "INTERMISSION"


def test_market_status_session2() -> None:
    broadcaster = MarketStatusBroadcaster()
    wib = ZoneInfo("Asia/Jakarta")
    now = datetime(2025, 3, 3, 14, 0, 0, tzinfo=wib)

    with patch(
        "strategy_engine.idx_trading_calendar.is_trading_day",
        return_value=True,
    ):
        status = broadcaster.get_current_status(now)

    assert status.status == "OPEN"
    assert status.session == "SESSION_2"


def test_market_status_holiday() -> None:
    broadcaster = MarketStatusBroadcaster()
    wib = ZoneInfo("Asia/Jakarta")
    now = datetime(2025, 12, 25, 10, 0, 0, tzinfo=wib)

    with patch(
        "strategy_engine.idx_trading_calendar.is_trading_day",
        return_value=False,
    ):
        status = broadcaster.get_current_status(now)

    assert status.status == "CLOSED"
    assert status.session == "HOLIDAY"


# ── Test 10: Kafka-Redis bridge transforms EOD to QUOTE_UPDATE ───────────


async def test_bridge_transforms_eod_to_quote_update() -> None:
    mock_kafka = MagicMock()
    mock_redis = _mock_redis()
    router = MessageRouter()

    bridge = KafkaRedisBridge(
        topic=KafkaTopic.VALIDATED_EOD_OHLCV,
        kafka_consumer=mock_kafka,
        redis_client=mock_redis,
        router=router,
    )

    eod_payload: dict[str, str] = {
        "symbol": "BBCA",
        "date": "2025-03-03",
        "open": "9200",
        "high": "9300",
        "low": "9150",
        "close": "9250",
        "volume": "12450000",
        "source": "eodhd",
    }

    channel, ws_message = await bridge._transform_message(KafkaTopic.VALIDATED_EOD_OHLCV, eod_payload)
    assert channel == "pyhron:quotes:BBCA"
    assert ws_message["type"] == "QUOTE_UPDATE"
    assert ws_message["symbol"] == "BBCA"
    assert ws_message["close"] == "9250"


async def test_bridge_transforms_order_to_order_update() -> None:
    mock_kafka = MagicMock()
    mock_redis = _mock_redis()
    router = MessageRouter()

    bridge = KafkaRedisBridge(
        topic=KafkaTopic.ORDER_FILLED,
        kafka_consumer=mock_kafka,
        redis_client=mock_redis,
        router=router,
    )

    order_payload: dict[str, Any] = {
        "user_id": "user-001",
        "order_id": "ord-123",
        "client_order_id": "cli-456",
        "symbol": "BBRI",
        "side": "BUY",
        "order_type": "LIMIT",
        "status": "FILLED",
        "quantity_lots": 10,
        "filled_quantity_lots": 10,
        "limit_price": "4500",
        "avg_fill_price": "4500",
    }

    channel, ws_message = await bridge._transform_message(KafkaTopic.ORDER_FILLED, order_payload)
    assert channel == "pyhron:orders:user-001"
    assert ws_message["type"] == "ORDER_UPDATE"
    assert ws_message["symbol"] == "BBRI"
    assert ws_message["status"] == "FILLED"
