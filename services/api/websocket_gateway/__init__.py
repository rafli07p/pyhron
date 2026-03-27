"""Pyhron WebSocket Gateway.

Provides real-time streaming of market data, order updates, and
portfolio events over WebSocket connections.  Supports per-symbol
subscriptions, JWT authentication on connect, heartbeat/ping-pong,
and broadcast to all subscribers of a channel.
"""

from __future__ import annotations

import asyncio
import json
import time
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any
from uuid import uuid4

import jwt
import structlog
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, status
from pydantic import BaseModel, Field

logger = structlog.stdlib.get_logger(__name__)

# Configuration

from shared.configuration_settings import get_config as _get_config


def _get_jwt_secret() -> str:
    return _get_config().jwt_secret_key


def _get_jwt_algorithm() -> str:
    return _get_config().jwt_algorithm


HEARTBEAT_INTERVAL_SECONDS = 15
HEARTBEAT_TIMEOUT_SECONDS = 30


# Message types


class WSMessageType(StrEnum):
    SUBSCRIBE = "subscribe"
    UNSUBSCRIBE = "unsubscribe"
    MARKET_DATA = "market_data"
    ORDER_UPDATE = "order_update"
    PORTFOLIO_UPDATE = "portfolio_update"
    HEARTBEAT = "heartbeat"
    ERROR = "error"
    ACK = "ack"


class WSMessage(BaseModel):
    type: WSMessageType
    channel: str | None = None
    symbol: str | None = None
    data: dict[str, Any] | None = None
    timestamp: datetime = Field(default_factory=lambda: datetime.now(tz=UTC))
    request_id: str | None = None


# Connection manager


class ConnectionManager:
    """Manages WebSocket connections and per-symbol subscriptions.

    Tracks active connections, their tenant/user context, symbol
    subscriptions, and provides broadcast capabilities.
    """

    def __init__(self) -> None:
        # connection_id -> WebSocket
        self._connections: dict[str, WebSocket] = {}
        # connection_id -> {"tenant_id": ..., "user_id": ..., "role": ...}
        self._connection_meta: dict[str, dict[str, str]] = {}
        # symbol -> set of connection_ids
        self._subscriptions: dict[str, set[str]] = {}
        # channel -> set of connection_ids  (order_updates, portfolio_updates)
        self._channel_subs: dict[str, set[str]] = {}
        # connection_id -> last pong timestamp
        self._last_pong: dict[str, float] = {}
        self._lock = asyncio.Lock()

    async def connect(
        self,
        websocket: WebSocket,
        connection_id: str,
        tenant_id: str,
        user_id: str,
        role: str,
    ) -> None:
        await websocket.accept()
        async with self._lock:
            self._connections[connection_id] = websocket
            self._connection_meta[connection_id] = {
                "tenant_id": tenant_id,
                "user_id": user_id,
                "role": role,
            }
            self._last_pong[connection_id] = time.monotonic()
        logger.info("ws_connected", connection_id=connection_id, tenant_id=tenant_id, user_id=user_id)

    async def disconnect(self, connection_id: str) -> None:
        async with self._lock:
            self._connections.pop(connection_id, None)
            self._connection_meta.pop(connection_id, None)
            self._last_pong.pop(connection_id, None)
            # Remove from all subscriptions
            for symbol, subs in list(self._subscriptions.items()):
                subs.discard(connection_id)
                if not subs:
                    del self._subscriptions[symbol]
            for channel, subs in list(self._channel_subs.items()):
                subs.discard(connection_id)
                if not subs:
                    del self._channel_subs[channel]
        logger.info("ws_disconnected", connection_id=connection_id)

    async def subscribe(self, connection_id: str, symbol: str) -> None:
        async with self._lock:
            self._subscriptions.setdefault(symbol, set()).add(connection_id)
        logger.info("ws_subscribed", connection_id=connection_id, symbol=symbol)

    async def unsubscribe(self, connection_id: str, symbol: str) -> None:
        async with self._lock:
            if symbol in self._subscriptions:
                self._subscriptions[symbol].discard(connection_id)
                if not self._subscriptions[symbol]:
                    del self._subscriptions[symbol]
        logger.info("ws_unsubscribed", connection_id=connection_id, symbol=symbol)

    async def subscribe_channel(self, connection_id: str, channel: str) -> None:
        async with self._lock:
            self._channel_subs.setdefault(channel, set()).add(connection_id)

    async def unsubscribe_channel(self, connection_id: str, channel: str) -> None:
        async with self._lock:
            if channel in self._channel_subs:
                self._channel_subs[channel].discard(connection_id)

    async def broadcast_market_data(self, symbol: str, data: dict[str, Any]) -> None:
        """Send market data to all connections subscribed to a symbol."""
        msg = WSMessage(
            type=WSMessageType.MARKET_DATA,
            symbol=symbol,
            data=data,
        )
        payload = msg.model_dump_json()
        async with self._lock:
            connection_ids = list(self._subscriptions.get(symbol, set()))
        for cid in connection_ids:
            ws = self._connections.get(cid)
            if ws:
                try:
                    await ws.send_text(payload)
                except Exception:
                    logger.warning("ws_send_failed", connection_id=cid, symbol=symbol)
                    await self.disconnect(cid)

    async def broadcast_channel(self, channel: str, data: dict[str, Any], tenant_id: str | None = None) -> None:
        """Broadcast to all subscribers of a named channel.

        If ``tenant_id`` is provided, only connections belonging to
        that tenant receive the message.
        """
        msg_type = {
            "order_updates": WSMessageType.ORDER_UPDATE,
            "portfolio_updates": WSMessageType.PORTFOLIO_UPDATE,
        }.get(channel, WSMessageType.MARKET_DATA)

        msg = WSMessage(type=msg_type, channel=channel, data=data)
        payload = msg.model_dump_json()

        async with self._lock:
            connection_ids = list(self._channel_subs.get(channel, set()))

        for cid in connection_ids:
            if tenant_id and self._connection_meta.get(cid, {}).get("tenant_id") != tenant_id:
                continue
            ws = self._connections.get(cid)
            if ws:
                try:
                    await ws.send_text(payload)
                except Exception:
                    logger.warning("ws_channel_send_failed", connection_id=cid, channel=channel)
                    await self.disconnect(cid)

    async def send_personal(self, connection_id: str, message: WSMessage) -> None:
        ws = self._connections.get(connection_id)
        if ws:
            try:
                await ws.send_text(message.model_dump_json())
            except Exception:
                await self.disconnect(connection_id)

    def record_pong(self, connection_id: str) -> None:
        self._last_pong[connection_id] = time.monotonic()

    async def check_stale_connections(self) -> list[str]:
        """Return connection IDs that have not responded to pings."""
        now = time.monotonic()
        stale: list[str] = []
        async with self._lock:
            for cid, last in list(self._last_pong.items()):
                if now - last > HEARTBEAT_TIMEOUT_SECONDS:
                    stale.append(cid)
        return stale

    @property
    def active_connections(self) -> int:
        return len(self._connections)


# Singleton connection manager
manager = ConnectionManager()


# JWT authentication for WebSocket


async def _authenticate_first_message(websocket: WebSocket) -> dict[str, str] | None:
    """Accept the WebSocket and authenticate via the first message.

    Clients must send ``{"type": "auth", "token": "<jwt>"}`` within 10 s.
    Returns the decoded claims dict on success, or ``None`` after closing
    the connection on failure.
    """
    await websocket.accept()
    try:
        raw = await asyncio.wait_for(websocket.receive_text(), timeout=10.0)
    except (TimeoutError, WebSocketDisconnect):
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="Auth timeout")
        return None

    try:
        auth_msg = json.loads(raw)
    except json.JSONDecodeError:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="Invalid JSON")
        return None

    if auth_msg.get("type") != "auth" or not auth_msg.get("token"):
        await websocket.close(
            code=status.WS_1008_POLICY_VIOLATION,
            reason='First message must be {"type": "auth", "token": "..."}',
        )
        return None

    try:
        return authenticate_ws_token(auth_msg["token"])
    except ValueError as exc:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason=str(exc))
        return None


def authenticate_ws_token(token: str) -> dict[str, str]:
    """Validate JWT and return claims.  Raises ValueError on failure."""
    try:
        payload = jwt.decode(token, _get_jwt_secret(), algorithms=[_get_jwt_algorithm()])
        required = {"sub", "tenant_id"}
        if not required.issubset(payload.keys()):
            raise ValueError("Missing required claims")
        return {
            "user_id": payload["sub"],
            "tenant_id": payload["tenant_id"],
            "role": payload.get("role", "viewer"),
        }
    except jwt.ExpiredSignatureError:
        raise ValueError("Token expired")
    except jwt.InvalidTokenError as exc:
        raise ValueError(f"Invalid token: {exc}") from exc


# Heartbeat background task


async def _heartbeat_loop() -> None:
    """Periodically send pings and disconnect stale clients."""
    while True:
        await asyncio.sleep(HEARTBEAT_INTERVAL_SECONDS)
        stale = await manager.check_stale_connections()
        for cid in stale:
            logger.warning("ws_stale_connection", connection_id=cid)
            await manager.disconnect(cid)

        # Send heartbeat to all active connections
        hb = WSMessage(type=WSMessageType.HEARTBEAT, data={"server_time": datetime.now(tz=UTC).isoformat()})
        payload = hb.model_dump_json()
        for cid, ws in list(manager._connections.items()):
            try:
                await ws.send_text(payload)
            except Exception:
                await manager.disconnect(cid)


# Market data feed background task (Polygon WebSocket)


async def _polygon_market_feed() -> None:
    """Connect to Polygon.io WebSocket and relay quotes to subscribers.

    Only runs when POLYGON_API_KEY is set.  Subscribes to symbols that
    have active WebSocket subscribers and broadcasts ticks.
    """
    import os

    api_key = os.environ.get("POLYGON_API_KEY", "")
    if not api_key:
        logger.info("polygon_ws_feed_disabled", reason="no POLYGON_API_KEY")
        return

    import websockets

    uri = "wss://socket.polygon.io/stocks"
    while True:
        try:
            async with websockets.connect(uri) as ws:
                # Authenticate
                await ws.send(json.dumps({"action": "auth", "params": api_key}))
                auth_resp = await ws.recv()
                logger.info("polygon_ws_authenticated", response=auth_resp[:100])

                subscribed_symbols: set[str] = set()

                while True:
                    # Sync subscriptions with current manager subscriptions
                    current_symbols = set(manager._subscriptions.keys())
                    to_add = current_symbols - subscribed_symbols
                    to_remove = subscribed_symbols - current_symbols

                    for sym in to_add:
                        await ws.send(json.dumps({"action": "subscribe", "params": f"Q.{sym}"}))
                        subscribed_symbols.add(sym)

                    for sym in to_remove:
                        await ws.send(json.dumps({"action": "unsubscribe", "params": f"Q.{sym}"}))
                        subscribed_symbols.discard(sym)

                    try:
                        raw = await asyncio.wait_for(ws.recv(), timeout=1.0)
                        messages = json.loads(raw)
                        if isinstance(messages, list):
                            for msg in messages:
                                ev = msg.get("ev")
                                sym = msg.get("sym") or msg.get("T", "")
                                if ev == "Q" and sym:
                                    await manager.broadcast_market_data(
                                        sym,
                                        {
                                            "bid": msg.get("bp", 0),
                                            "ask": msg.get("ap", 0),
                                            "bid_size": msg.get("bs", 0),
                                            "ask_size": msg.get("as", 0),
                                            "timestamp": msg.get("t"),
                                        },
                                    )
                                elif ev == "T" and sym:
                                    await manager.broadcast_market_data(
                                        sym,
                                        {
                                            "price": msg.get("p", 0),
                                            "size": msg.get("s", 0),
                                            "timestamp": msg.get("t"),
                                        },
                                    )
                    except TimeoutError:
                        continue

        except Exception:
            logger.exception("polygon_ws_error")
            await asyncio.sleep(5)


# Application factory


def create_ws_app() -> FastAPI:
    """Build and return the WebSocket gateway FastAPI app."""
    app = FastAPI(
        title="Pyhron WebSocket Gateway",
        description="Real-time streaming gateway for market data, orders, and portfolio events",
        version="0.1.0",
    )

    _background_tasks: list[asyncio.Task[None]] = []

    @app.on_event("startup")
    async def startup() -> None:
        _background_tasks.append(asyncio.create_task(_heartbeat_loop()))
        _background_tasks.append(asyncio.create_task(_polygon_market_feed()))
        logger.info("ws_gateway_started")

    @app.get("/health")
    async def health() -> dict[str, Any]:
        return {
            "status": "ok",
            "active_connections": manager.active_connections,
            "timestamp": datetime.now(tz=UTC).isoformat(),
        }

    # Main WebSocket endpoint

    @app.websocket("/ws")
    async def websocket_endpoint(
        websocket: WebSocket,
    ) -> None:
        """Primary WebSocket endpoint.

        Clients connect without a token, then send a first message of
        ``{"type": "auth", "token": "<jwt>"}`` to authenticate.  After
        successful authentication they may subscribe/unsubscribe to
        symbols and channels.
        """
        await websocket.accept()

        # Wait for auth message as the first message
        try:
            raw = await asyncio.wait_for(websocket.receive_text(), timeout=10.0)
        except (TimeoutError, WebSocketDisconnect):
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="Auth timeout")
            return

        try:
            auth_msg = json.loads(raw)
        except json.JSONDecodeError:
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="Invalid JSON")
            return

        if auth_msg.get("type") != "auth" or not auth_msg.get("token"):
            await websocket.close(
                code=status.WS_1008_POLICY_VIOLATION,
                reason='First message must be {"type": "auth", "token": "..."}',
            )
            return

        try:
            claims = authenticate_ws_token(auth_msg["token"])
        except ValueError as exc:
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason=str(exc))
            return

        connection_id = str(uuid4())
        # Connection already accepted above, so register directly
        async with manager._lock:
            manager._connections[connection_id] = websocket
            manager._connection_meta[connection_id] = {
                "tenant_id": claims["tenant_id"],
                "user_id": claims["user_id"],
                "role": claims["role"],
            }
            manager._last_pong[connection_id] = time.monotonic()
        logger.info(
            "ws_connected", connection_id=connection_id, tenant_id=claims["tenant_id"], user_id=claims["user_id"]
        )

        # Send welcome message
        await manager.send_personal(
            connection_id,
            WSMessage(
                type=WSMessageType.ACK,
                data={"connection_id": connection_id, "message": "Connected to Pyhron WebSocket Gateway"},
            ),
        )

        try:
            while True:
                raw = await websocket.receive_text()
                try:
                    msg = json.loads(raw)
                except json.JSONDecodeError:
                    await manager.send_personal(
                        connection_id,
                        WSMessage(
                            type=WSMessageType.ERROR,
                            data={"error": "Invalid JSON"},
                        ),
                    )
                    continue

                msg_type = msg.get("type", "")
                symbol = msg.get("symbol")
                channel = msg.get("channel")
                request_id = msg.get("request_id")

                if msg_type == WSMessageType.SUBSCRIBE:
                    if symbol:
                        await manager.subscribe(connection_id, symbol)
                    if channel:
                        await manager.subscribe_channel(connection_id, channel)
                    await manager.send_personal(
                        connection_id,
                        WSMessage(
                            type=WSMessageType.ACK,
                            data={"action": "subscribed", "symbol": symbol, "channel": channel},
                            request_id=request_id,
                        ),
                    )

                elif msg_type == WSMessageType.UNSUBSCRIBE:
                    if symbol:
                        await manager.unsubscribe(connection_id, symbol)
                    if channel:
                        await manager.unsubscribe_channel(connection_id, channel)
                    await manager.send_personal(
                        connection_id,
                        WSMessage(
                            type=WSMessageType.ACK,
                            data={"action": "unsubscribed", "symbol": symbol, "channel": channel},
                            request_id=request_id,
                        ),
                    )

                elif msg_type == WSMessageType.HEARTBEAT:
                    # Client pong
                    manager.record_pong(connection_id)

                else:
                    await manager.send_personal(
                        connection_id,
                        WSMessage(
                            type=WSMessageType.ERROR,
                            data={"error": f"Unknown message type: {msg_type}"},
                            request_id=request_id,
                        ),
                    )

        except WebSocketDisconnect:
            await manager.disconnect(connection_id)
        except Exception:
            logger.exception("ws_handler_error", connection_id=connection_id)
            await manager.disconnect(connection_id)

    # Dedicated market data WebSocket

    @app.websocket("/ws/market-data")
    async def market_data_ws(
        websocket: WebSocket,
    ) -> None:
        """Dedicated WebSocket for market data streaming.

        Clients authenticate via the first message:
        ``{"type": "auth", "token": "<jwt>"}``, then send
        subscribe/unsubscribe messages for individual symbols.
        """
        claims = await _authenticate_first_message(websocket)
        if claims is None:
            return

        connection_id = str(uuid4())
        # Connection already accepted by _authenticate_first_message
        async with manager._lock:
            manager._connections[connection_id] = websocket
            manager._connection_meta[connection_id] = {
                "tenant_id": claims["tenant_id"],
                "user_id": claims["user_id"],
                "role": claims["role"],
            }
            manager._last_pong[connection_id] = time.monotonic()

        try:
            while True:
                raw = await websocket.receive_text()
                msg = json.loads(raw)
                action = msg.get("type", "")
                symbol = msg.get("symbol", "")

                if action == "subscribe" and symbol:
                    await manager.subscribe(connection_id, symbol)
                    await websocket.send_text(
                        WSMessage(
                            type=WSMessageType.ACK,
                            data={"subscribed": symbol},
                        ).model_dump_json()
                    )
                elif action == "unsubscribe" and symbol:
                    await manager.unsubscribe(connection_id, symbol)
                    await websocket.send_text(
                        WSMessage(
                            type=WSMessageType.ACK,
                            data={"unsubscribed": symbol},
                        ).model_dump_json()
                    )
                elif action == "heartbeat":
                    manager.record_pong(connection_id)

        except WebSocketDisconnect:
            await manager.disconnect(connection_id)
        except Exception:
            logger.exception("market_data_ws_error", connection_id=connection_id)
            await manager.disconnect(connection_id)

    # Dedicated order updates WebSocket

    @app.websocket("/ws/orders")
    async def orders_ws(
        websocket: WebSocket,
    ) -> None:
        """WebSocket for real-time order status updates.

        Clients authenticate via the first message:
        ``{"type": "auth", "token": "<jwt>"}``.  Auto-subscribes
        to the ``order_updates`` channel filtered by the
        authenticated tenant.
        """
        claims = await _authenticate_first_message(websocket)
        if claims is None:
            return

        connection_id = str(uuid4())
        async with manager._lock:
            manager._connections[connection_id] = websocket
            manager._connection_meta[connection_id] = {
                "tenant_id": claims["tenant_id"],
                "user_id": claims["user_id"],
                "role": claims["role"],
            }
            manager._last_pong[connection_id] = time.monotonic()
        await manager.subscribe_channel(connection_id, "order_updates")

        try:
            while True:
                raw = await websocket.receive_text()
                msg = json.loads(raw)
                if msg.get("type") == "heartbeat":
                    manager.record_pong(connection_id)
        except WebSocketDisconnect:
            await manager.disconnect(connection_id)
        except Exception:
            logger.exception("orders_ws_error", connection_id=connection_id)
            await manager.disconnect(connection_id)

    # Dedicated portfolio updates WebSocket

    @app.websocket("/ws/portfolio")
    async def portfolio_ws(
        websocket: WebSocket,
    ) -> None:
        """WebSocket for real-time portfolio / P&L updates.

        Clients authenticate via the first message:
        ``{"type": "auth", "token": "<jwt>"}``.  Auto-subscribes
        to the ``portfolio_updates`` channel.
        """
        claims = await _authenticate_first_message(websocket)
        if claims is None:
            return

        connection_id = str(uuid4())
        async with manager._lock:
            manager._connections[connection_id] = websocket
            manager._connection_meta[connection_id] = {
                "tenant_id": claims["tenant_id"],
                "user_id": claims["user_id"],
                "role": claims["role"],
            }
            manager._last_pong[connection_id] = time.monotonic()
        await manager.subscribe_channel(connection_id, "portfolio_updates")

        try:
            while True:
                raw = await websocket.receive_text()
                msg = json.loads(raw)
                if msg.get("type") == "heartbeat":
                    manager.record_pong(connection_id)
        except WebSocketDisconnect:
            await manager.disconnect(connection_id)
        except Exception:
            logger.exception("portfolio_ws_error", connection_id=connection_id)
            await manager.disconnect(connection_id)

    return app


__all__ = [
    "ConnectionManager",
    "WSMessage",
    "WSMessageType",
    "create_ws_app",
    "manager",
]
