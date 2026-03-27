"""WebSocket endpoint for the Pyhron real-time terminal feed.

Handles the full connection lifecycle: accept → authenticate → subscribe
→ message loop → disconnect.
"""

from __future__ import annotations

import asyncio
import logging
from datetime import UTC, datetime
from typing import TYPE_CHECKING
from uuid import uuid4

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

if TYPE_CHECKING:
    from services.api.websocket_gateway.connection_manager import (
        WebSocketConnectionManager,
    )
    from services.api.websocket_gateway.ws_rate_limiter import WebSocketRateLimiter

logger = logging.getLogger(__name__)

router = APIRouter()

AUTH_TIMEOUT_SECONDS = 10


async def _get_manager(websocket: WebSocket) -> WebSocketConnectionManager:
    """Retrieve the connection manager from the app state."""
    return websocket.app.state.ws_manager  # type: ignore[no-any-return]


async def _get_rate_limiter(websocket: WebSocket) -> WebSocketRateLimiter:
    """Retrieve the rate limiter from the app state."""
    return websocket.app.state.ws_rate_limiter  # type: ignore[no-any-return]


@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket) -> None:
    """Main WebSocket endpoint for the Pyhron terminal.

    Connection flow
    ---------------
    1. Accept connection, generate ``connection_id`` (UUID)
    2. Wait for ``AUTH`` message with 10 s timeout
    3. Validate token; close 4001 if invalid
    4. Enforce ``MAX_CONNECTIONS_PER_USER``; close 4003 if exceeded
    5. Send ``AUTH_OK``
    6. Send initial ``MARKET_STATUS``
    7. Start heartbeat task
    8. Enter message-receive loop until disconnect
    """
    manager = await _get_manager(websocket)
    rate_limiter = await _get_rate_limiter(websocket)
    connection_id = str(uuid4())

    await manager.connect(websocket, connection_id)

    try:
        # Authentication phase (10 s timeout)
        try:
            raw = await asyncio.wait_for(
                websocket.receive_json(),
                timeout=AUTH_TIMEOUT_SECONDS,
            )
        except (TimeoutError, WebSocketDisconnect):
            await manager.disconnect(connection_id, code=4001, reason="auth_timeout")
            return

        if not isinstance(raw, dict) or raw.get("type") != "AUTH":
            await manager.send_to_connection(
                connection_id,
                {
                    "type": "AUTH_FAIL",
                    "reason": "first_message_must_be_auth",
                },
            )
            await manager.disconnect(connection_id, code=4001, reason="not_auth")
            return

        token = raw.get("token", "")
        user = await manager.authenticate(connection_id, str(token))
        if user is None:
            await manager.send_to_connection(
                connection_id,
                {
                    "type": "AUTH_FAIL",
                    "reason": "invalid_token",
                },
            )
            await manager.disconnect(connection_id, code=4001, reason="auth_failed")
            return

        # Send AUTH_OK
        await manager.send_to_connection(
            connection_id,
            {
                "type": "AUTH_OK",
                "user_id": user.user_id,
                "username": user.username,
                "role": user.role,
                "server_time": datetime.now(UTC).isoformat(),
            },
        )

        # Send initial MARKET_STATUS
        from services.api.websocket_gateway.initial_state_provider import (
            InitialStateProvider,
        )

        state_provider = InitialStateProvider(manager._redis)
        await state_provider.send_market_status(connection_id, manager)

        # Start heartbeat
        heartbeat_task = asyncio.create_task(
            manager.run_heartbeat_loop(connection_id),
            name=f"heartbeat:{connection_id}",
        )
        state = manager._connections.get(connection_id)
        if state is not None:
            state.heartbeat_task = heartbeat_task

        # Message loop
        while True:
            try:
                raw_message = await websocket.receive_json()
            except WebSocketDisconnect:
                break

            if not isinstance(raw_message, dict):
                continue

            # Rate limit check
            allowed = await rate_limiter.check_inbound(connection_id)
            if not allowed:
                await manager.send_to_connection(
                    connection_id,
                    {
                        "type": "ERROR",
                        "code": "rate_limit_exceeded",
                        "message": "Too many messages. Max 100 per minute.",
                    },
                )
                await manager.disconnect(connection_id, code=4004, reason="rate_limited")
                break

            await _handle_client_message(raw_message, connection_id, manager, rate_limiter)

    except WebSocketDisconnect:
        pass
    except Exception:
        logger.exception("ws.error connection_id=%s", connection_id)
    finally:
        await rate_limiter.cleanup(connection_id)
        await manager.disconnect(connection_id)


async def _handle_client_message(
    message: dict,  # type: ignore[type-arg]
    connection_id: str,
    manager: WebSocketConnectionManager,
    rate_limiter: WebSocketRateLimiter,
) -> None:
    """Route incoming client messages to appropriate handlers.

    Never raises — all errors are sent back as ``ERROR`` messages.
    """
    msg_type = message.get("type")

    if msg_type == "SUBSCRIBE":
        await _handle_subscribe(message, connection_id, manager, rate_limiter)
    elif msg_type == "UNSUBSCRIBE":
        await _handle_unsubscribe(message, connection_id, manager)
    elif msg_type == "PONG":
        manager.record_pong(connection_id)
    else:
        await manager.send_to_connection(
            connection_id,
            {
                "type": "ERROR",
                "code": "unknown_message_type",
                "message": f"Unrecognized message type: {msg_type}",
            },
        )


async def _handle_subscribe(
    message: dict,  # type: ignore[type-arg]
    connection_id: str,
    manager: WebSocketConnectionManager,
    rate_limiter: WebSocketRateLimiter,
) -> None:
    channel = str(message.get("channel", ""))
    key = str(message.get("key", ""))

    if not channel or not key:
        await manager.send_to_connection(
            connection_id,
            {
                "type": "ERROR",
                "code": "invalid_subscribe",
                "message": "channel and key are required",
            },
        )
        return

    allowed = await rate_limiter.check_subscribe(connection_id)
    if not allowed:
        await manager.send_to_connection(
            connection_id,
            {
                "type": "ERROR",
                "code": "subscribe_rate_limited",
                "message": "Too many subscribe requests.",
            },
        )
        return

    ok = await manager.subscribe(connection_id, channel, key)
    if ok:
        await manager.send_to_connection(
            connection_id,
            {
                "type": "SUBSCRIBED",
                "channel": channel,
                "key": key,
            },
        )
    else:
        await manager.send_to_connection(
            connection_id,
            {
                "type": "ERROR",
                "code": "subscribe_failed",
                "message": f"Cannot subscribe to {channel}:{key}",
            },
        )


async def _handle_unsubscribe(
    message: dict,  # type: ignore[type-arg]
    connection_id: str,
    manager: WebSocketConnectionManager,
) -> None:
    channel = str(message.get("channel", ""))
    key = str(message.get("key", ""))
    await manager.unsubscribe(connection_id, channel, key)
