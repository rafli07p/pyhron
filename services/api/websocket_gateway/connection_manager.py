"""WebSocket connection manager for Pyhron real-time feed.

Central registry of all active WebSocket connections. Handles
subscription routing, message dispatch, and connection lifecycle.

Architecture
------------
Layer 2 of the two-layer fan-out:
  Redis pub/sub → ConnectionManager → WebSocket clients

Thread safety: all methods are async and must be called from the same
event loop.  ``asyncio.Lock`` guards mutations to the connection registry.
"""

from __future__ import annotations

import asyncio
import contextlib
import logging
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from shared.security.auth import TokenPayload, verify_token

if TYPE_CHECKING:
    import redis.asyncio as aioredis
    from starlette.websockets import WebSocket

logger = logging.getLogger(__name__)

# Channel type → Redis key prefix
_CHANNEL_PREFIXES: dict[str, str] = {
    "quotes": "pyhron:quotes:",
    "orders": "pyhron:orders:",
    "positions": "pyhron:positions:",
    "signals": "pyhron:signals:",
    "market": "pyhron:market:",
}


@dataclass
class AuthenticatedUser:
    """Authenticated identity attached to a WebSocket connection."""

    user_id: str
    tenant_id: str
    role: str
    username: str


@dataclass
class _ConnectionState:
    """Internal bookkeeping for a single WebSocket connection."""

    websocket: WebSocket
    connection_id: str
    user: AuthenticatedUser | None = None
    subscriptions: set[str] = field(default_factory=set)
    last_pong: datetime = field(default_factory=lambda: datetime.now(UTC))
    heartbeat_task: asyncio.Task[None] | None = None


class WebSocketConnectionManager:
    """Manages all active WebSocket connections for the Pyhron API.

    Connection lifecycle
    --------------------
    1. Client connects to ``/ws``
    2. Client sends ``AUTH`` message with JWT token
    3. Server validates token; on failure close with **4001**
    4. Client sends ``SUBSCRIBE`` messages for desired channels
    5. Server registers subscriptions and starts forwarding messages
    6. Server sends ``HEARTBEAT`` every 30 s; client must ``PONG`` within 10 s
    7. On ``PONG`` timeout: close connection with **4002**
    8. On disconnect: clean up all subscriptions and Redis listeners
    """

    HEARTBEAT_INTERVAL_SECONDS = 30
    PONG_TIMEOUT_SECONDS = 10
    MAX_CONNECTIONS_PER_USER = 5
    MAX_SUBSCRIPTIONS_PER_CONNECTION = 50

    def __init__(self, redis_client: aioredis.Redis) -> None:
        self._redis: aioredis.Redis = redis_client
        self._connections: dict[str, _ConnectionState] = {}
        # channel → set of connection_ids
        self._channel_subs: dict[str, set[str]] = {}
        # user_id → set of connection_ids (for per-user limit)
        self._user_connections: dict[str, set[str]] = {}
        self._lock = asyncio.Lock()

    # Connection lifecycle

    async def connect(self, websocket: WebSocket, connection_id: str) -> None:
        """Accept the WebSocket and register it (unauthenticated)."""
        await websocket.accept()
        async with self._lock:
            self._connections[connection_id] = _ConnectionState(
                websocket=websocket,
                connection_id=connection_id,
            )
        logger.info("ws.connect connection_id=%s", connection_id)

    async def authenticate(
        self,
        connection_id: str,
        token: str,
    ) -> AuthenticatedUser | None:
        """Validate JWT.  Returns ``AuthenticatedUser`` on success, else ``None``."""
        try:
            payload: TokenPayload = verify_token(token)
        except Exception:
            logger.warning("ws.auth_fail connection_id=%s", connection_id)
            return None

        user_id = str(payload.sub)
        tenant_id = str(payload.tenant_id)
        role = str(payload.role) if payload.role else "VIEWER"
        username = user_id  # JWT sub is the canonical identity

        async with self._lock:
            state = self._connections.get(connection_id)
            if state is None:
                return None

            # Enforce per-user connection limit
            existing = self._user_connections.get(user_id, set())
            if len(existing) >= self.MAX_CONNECTIONS_PER_USER:
                logger.warning(
                    "ws.max_connections user_id=%s count=%d",
                    user_id,
                    len(existing),
                )
                return None

            user = AuthenticatedUser(
                user_id=user_id,
                tenant_id=tenant_id,
                role=role,
                username=username,
            )
            state.user = user
            self._user_connections.setdefault(user_id, set()).add(connection_id)

        logger.info("ws.authenticated connection_id=%s user_id=%s", connection_id, user_id)
        return user

    # Subscription management

    async def subscribe(
        self,
        connection_id: str,
        channel_type: str,
        channel_key: str,
    ) -> bool:
        """Register a subscription.  Returns ``False`` on limit or invalid."""
        prefix = _CHANNEL_PREFIXES.get(channel_type)
        if prefix is None:
            return False

        channel = f"{prefix}{channel_key}"

        async with self._lock:
            state = self._connections.get(connection_id)
            if state is None or state.user is None:
                return False
            if len(state.subscriptions) >= self.MAX_SUBSCRIPTIONS_PER_CONNECTION:
                return False
            state.subscriptions.add(channel)
            self._channel_subs.setdefault(channel, set()).add(connection_id)

        logger.debug("ws.subscribe connection_id=%s channel=%s", connection_id, channel)
        return True

    async def unsubscribe(
        self,
        connection_id: str,
        channel_type: str,
        channel_key: str,
    ) -> None:
        prefix = _CHANNEL_PREFIXES.get(channel_type)
        if prefix is None:
            return
        channel = f"{prefix}{channel_key}"

        async with self._lock:
            state = self._connections.get(connection_id)
            if state is None:
                return
            state.subscriptions.discard(channel)
            subs = self._channel_subs.get(channel)
            if subs is not None:
                subs.discard(connection_id)
                if not subs:
                    del self._channel_subs[channel]

    # Message dispatch

    async def broadcast_to_channel(self, channel: str, message: dict) -> int:  # type: ignore[type-arg]
        """Send *message* to every connection subscribed to *channel*.

        Returns the number of connections that received the message.
        Failed sends trigger a disconnect for that connection.
        """
        async with self._lock:
            conn_ids = list(self._channel_subs.get(channel, set()))

        sent = 0
        stale: list[str] = []
        for cid in conn_ids:
            ok = await self.send_to_connection(cid, message)
            if ok:
                sent += 1
            else:
                stale.append(cid)

        for cid in stale:
            await self.disconnect(cid, code=1011, reason="send_failed")
        return sent

    async def send_to_connection(self, connection_id: str, message: dict) -> bool:  # type: ignore[type-arg]
        """Send *message* to a single connection.  Returns ``False`` on failure."""
        state = self._connections.get(connection_id)
        if state is None:
            return False
        try:
            await state.websocket.send_json(message)
            return True
        except Exception:
            logger.debug("ws.send_fail connection_id=%s", connection_id)
            return False

    # Disconnect / cleanup

    async def disconnect(
        self,
        connection_id: str,
        code: int = 1000,
        reason: str = "",
    ) -> None:
        """Close connection and remove all state."""
        async with self._lock:
            state = self._connections.pop(connection_id, None)
            if state is None:
                return

            # Cancel heartbeat task
            if state.heartbeat_task is not None and not state.heartbeat_task.done():
                state.heartbeat_task.cancel()

            # Remove channel subscriptions
            for ch in state.subscriptions:
                subs = self._channel_subs.get(ch)
                if subs is not None:
                    subs.discard(connection_id)
                    if not subs:
                        del self._channel_subs[ch]

            # Remove user tracking
            if state.user is not None:
                uid_set = self._user_connections.get(state.user.user_id)
                if uid_set is not None:
                    uid_set.discard(connection_id)
                    if not uid_set:
                        del self._user_connections[state.user.user_id]

        # Close WebSocket outside the lock
        with contextlib.suppress(Exception):
            await state.websocket.close(code=code, reason=reason)

        logger.info("ws.disconnect connection_id=%s code=%d", connection_id, code)

    # Heartbeat

    async def run_heartbeat_loop(self, connection_id: str) -> None:
        """Send ``HEARTBEAT`` periodically; close on PONG timeout."""
        try:
            while True:
                await asyncio.sleep(self.HEARTBEAT_INTERVAL_SECONDS)
                state = self._connections.get(connection_id)
                if state is None:
                    return

                heartbeat_msg = {
                    "type": "HEARTBEAT",
                    "server_time": datetime.now(UTC).isoformat(),
                    "connection_id": connection_id,
                }
                ok = await self.send_to_connection(connection_id, heartbeat_msg)
                if not ok:
                    await self.disconnect(connection_id, code=1011, reason="send_failed")
                    return

                # Wait for PONG
                await asyncio.sleep(self.PONG_TIMEOUT_SECONDS)
                state = self._connections.get(connection_id)
                if state is None:
                    return
                elapsed = (datetime.now(UTC) - state.last_pong).total_seconds()
                if elapsed > self.HEARTBEAT_INTERVAL_SECONDS + self.PONG_TIMEOUT_SECONDS:
                    logger.warning("ws.pong_timeout connection_id=%s", connection_id)
                    await self.disconnect(connection_id, code=4002, reason="pong_timeout")
                    return
        except asyncio.CancelledError:
            return

    def record_pong(self, connection_id: str) -> None:
        """Record a PONG from the client."""
        state = self._connections.get(connection_id)
        if state is not None:
            state.last_pong = datetime.now(UTC)

    # Introspection helpers

    def is_connected(self, connection_id: str) -> bool:
        return connection_id in self._connections

    def is_authenticated(self, connection_id: str) -> bool:
        state = self._connections.get(connection_id)
        return state is not None and state.user is not None

    def get_user(self, connection_id: str) -> AuthenticatedUser | None:
        state = self._connections.get(connection_id)
        return state.user if state else None

    @property
    def active_connections(self) -> int:
        return len(self._connections)
