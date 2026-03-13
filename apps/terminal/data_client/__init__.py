"""Data Client for the Pyhron Terminal.

HTTP and WebSocket client that consumes the services/api layer. Provides
methods for fetching market data, subscribing to real-time streams,
submitting orders, querying portfolios, and running backtests.

Uses ``httpx`` for HTTP requests and the Pyhron WebSocket protocol
(AUTH → SUBSCRIBE → message loop) for real-time streaming with
automatic reconnection and exponential backoff.
"""

from __future__ import annotations

import asyncio
import contextlib
import json
import logging
from collections.abc import Callable
from datetime import UTC, datetime
from typing import Any, cast

import httpx

logger = logging.getLogger(__name__)

_DEFAULT_BASE_URL = "http://localhost:8000/api/v1"
_DEFAULT_WS_URL = "ws://localhost:8000/ws"

# Reconnection backoff parameters
_RECONNECT_BASE_SECONDS = 1
_RECONNECT_MAX_SECONDS = 60


class DataClient:
    """HTTP/WebSocket client for consuming Pyhron services.

    Implements the full WebSocket protocol from the Pyhron real-time feed:
    - AUTH → AUTH_OK on connect
    - SUBSCRIBE for each channel
    - HEARTBEAT/PONG keepalive
    - Automatic reconnection with exponential backoff
    - Local subscription registry for replay after reconnect
    """

    def __init__(
        self,
        base_url: str = _DEFAULT_BASE_URL,
        ws_url: str = _DEFAULT_WS_URL,
        api_key: str | None = None,
        tenant_id: str = "default",
        timeout: float = 30.0,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._ws_url = ws_url.rstrip("/")
        self._api_key = api_key
        self._tenant_id = tenant_id
        self._timeout = timeout
        self._http_client: httpx.AsyncClient | None = None

        # WebSocket state
        self._ws: Any = None
        self._ws_task: asyncio.Task[None] | None = None
        self._authenticated_user_id: str | None = None

        # Local subscription registry for replay on reconnect
        self._active_subscriptions: dict[str, str] = {}  # "channel:key" → key
        self._callbacks: dict[str, Callable[..., Any]] = {}  # msg_type → callback
        self._connection_status_callback: Callable[[str], Any] | None = None

        # Reconnection state
        self._should_reconnect = True
        self._reconnect_attempt = 0

        logger.info("DataClient initialized (base_url=%s, tenant_id=%s)", base_url, tenant_id)

    @property
    def is_connected(self) -> bool:
        return self._http_client is not None and not self._http_client.is_closed

    @property
    def is_ws_connected(self) -> bool:
        return self._ws is not None

    # ------------------------------------------------------------------
    # HTTP lifecycle
    # ------------------------------------------------------------------

    async def connect(self) -> None:
        """Initialize the HTTP client session."""
        headers: dict[str, str] = {
            "Content-Type": "application/json",
            "X-Tenant-ID": self._tenant_id,
        }
        if self._api_key:
            headers["Authorization"] = f"Bearer {self._api_key}"

        self._http_client = httpx.AsyncClient(
            base_url=self._base_url,
            headers=headers,
            timeout=httpx.Timeout(self._timeout),
        )
        logger.info("HTTP client connected to %s", self._base_url)

    async def disconnect(self) -> None:
        """Close all connections."""
        self._should_reconnect = False

        if self._ws_task and not self._ws_task.done():
            self._ws_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._ws_task

        if self._ws is not None:
            with contextlib.suppress(Exception):
                await self._ws.close()
            self._ws = None

        if self._http_client and not self._http_client.is_closed:
            await self._http_client.aclose()

        logger.info("DataClient disconnected")

    async def _ensure_connected(self) -> httpx.AsyncClient:
        if not self.is_connected:
            await self.connect()
        assert self._http_client is not None
        return self._http_client

    # ------------------------------------------------------------------
    # WebSocket connection
    # ------------------------------------------------------------------

    async def connect_websocket(self) -> None:
        """Establish WebSocket connection and authenticate.

        Sends ``AUTH`` immediately after connect, waits for ``AUTH_OK``,
        then starts the message dispatch loop as a background task.
        """
        try:
            import websockets
        except ImportError as err:
            raise ImportError("The 'websockets' package is required") from err

        self._should_reconnect = True
        self._reconnect_attempt = 0

        ws = await websockets.connect(self._ws_url)
        self._ws = ws

        # Send AUTH
        auth_msg = json.dumps({"type": "AUTH", "token": self._api_key or ""})
        await ws.send(auth_msg)

        # Wait for AUTH_OK or AUTH_FAIL
        raw = await asyncio.wait_for(ws.recv(), timeout=10)
        response = json.loads(raw)

        if response.get("type") == "AUTH_FAIL":
            reason = response.get("reason", "unknown")
            await ws.close()
            self._ws = None
            raise ConnectionError(f"WebSocket auth failed: {reason}")

        if response.get("type") == "AUTH_OK":
            self._authenticated_user_id = response.get("user_id")
            logger.info("WebSocket authenticated user_id=%s", self._authenticated_user_id)

        # Start background message dispatch
        self._ws_task = asyncio.create_task(
            self._message_dispatch_loop(),
            name="ws_dispatch",
        )

        self._notify_connection_status("connected")

    async def _message_dispatch_loop(self) -> None:
        """Receive messages and dispatch to registered callbacks.

        On disconnect: attempt reconnection with exponential backoff.
        """
        try:
            while self._ws is not None:
                try:
                    raw = await self._ws.recv()
                    message = json.loads(raw)
                    msg_type = message.get("type", "")

                    if msg_type == "HEARTBEAT":
                        self._on_heartbeat(message)
                    elif msg_type == "AUTH_FAIL":
                        self._on_auth_fail(message)
                        return
                    else:
                        callback = self._callbacks.get(msg_type)
                        if callback:
                            try:
                                result = callback(message)
                                if asyncio.iscoroutine(result):
                                    await result
                            except Exception:
                                logger.exception("callback_error type=%s", msg_type)

                except Exception:
                    logger.warning("ws.dispatch_loop disconnected")
                    self._ws = None
                    self._notify_connection_status("disconnected")

                    if not self._should_reconnect:
                        return

                    await self._attempt_reconnect()
                    return
        except asyncio.CancelledError:
            return

    async def _attempt_reconnect(self) -> None:
        """Reconnect with exponential backoff, replaying subscriptions."""
        while self._should_reconnect:
            delay = min(
                _RECONNECT_BASE_SECONDS * (2**self._reconnect_attempt),
                _RECONNECT_MAX_SECONDS,
            )
            logger.info("ws.reconnect attempt=%d delay=%ds", self._reconnect_attempt, delay)
            await asyncio.sleep(delay)
            self._reconnect_attempt += 1

            try:
                await self.connect_websocket()

                # Replay all active subscriptions
                for sub_key in list(self._active_subscriptions):
                    channel, key = sub_key.split(":", 1)
                    await self._send_subscribe(channel, key)

                self._reconnect_attempt = 0
                self._notify_connection_status("reconnected")
                return
            except Exception:
                logger.warning("ws.reconnect_failed attempt=%d", self._reconnect_attempt)

    async def _send_subscribe(self, channel: str, key: str) -> None:
        """Send a SUBSCRIBE message over WebSocket."""
        if self._ws is None:
            return
        msg = json.dumps({"type": "SUBSCRIBE", "channel": channel, "key": key})
        await self._ws.send(msg)

    # ------------------------------------------------------------------
    # Subscription API
    # ------------------------------------------------------------------

    async def subscribe_quotes(
        self,
        symbols: list[str],
        callback: Callable[[dict[str, Any]], Any],
    ) -> None:
        """Subscribe to quote updates for *symbols*."""
        self._callbacks["QUOTE_UPDATE"] = callback
        for symbol in symbols:
            sub_key = f"quotes:{symbol}"
            self._active_subscriptions[sub_key] = symbol
            await self._send_subscribe("quotes", symbol)

    async def subscribe_order_updates(
        self,
        callback: Callable[[dict[str, Any]], Any],
    ) -> None:
        """Subscribe to order updates for the authenticated user."""
        self._callbacks["ORDER_UPDATE"] = callback
        if self._authenticated_user_id:
            sub_key = f"orders:{self._authenticated_user_id}"
            self._active_subscriptions[sub_key] = self._authenticated_user_id
            await self._send_subscribe("orders", self._authenticated_user_id)

    async def subscribe_position_updates(
        self,
        callback: Callable[[dict[str, Any]], Any],
    ) -> None:
        """Subscribe to position updates for the authenticated user."""
        self._callbacks["POSITION_UPDATE"] = callback
        if self._authenticated_user_id:
            sub_key = f"positions:{self._authenticated_user_id}"
            self._active_subscriptions[sub_key] = self._authenticated_user_id
            await self._send_subscribe("positions", self._authenticated_user_id)

    async def subscribe_market_status(
        self,
        callback: Callable[[dict[str, Any]], Any],
    ) -> None:
        """Subscribe to market status broadcasts."""
        self._callbacks["MARKET_STATUS"] = callback
        sub_key = "market:status"
        self._active_subscriptions[sub_key] = "status"
        await self._send_subscribe("market", "status")

    def on_connection_status(self, callback: Callable[[str], Any]) -> None:
        """Register a callback for connection status changes."""
        self._connection_status_callback = callback

    # ------------------------------------------------------------------
    # Heartbeat / auth handlers
    # ------------------------------------------------------------------

    def _on_heartbeat(self, message: dict[str, Any]) -> None:
        """Respond to HEARTBEAT with PONG immediately."""
        if self._ws is not None:
            pong = json.dumps(
                {
                    "type": "PONG",
                    "timestamp": datetime.now(UTC).isoformat(),
                }
            )
            self._pong_task = asyncio.ensure_future(self._ws.send(pong))

    def _on_auth_fail(self, message: dict[str, Any]) -> None:
        """Handle AUTH_FAIL — log and close."""
        reason = message.get("reason", "unknown")
        logger.error("ws.auth_fail reason=%s", reason)
        self._should_reconnect = False

    def _notify_connection_status(self, status: str) -> None:
        if self._connection_status_callback:
            with contextlib.suppress(Exception):
                self._connection_status_callback(status)

    # ------------------------------------------------------------------
    # HTTP methods (unchanged)
    # ------------------------------------------------------------------

    async def get_market_data(
        self,
        symbol: str,
        timeframe: str = "1D",
        data_type: str = "bars",
        limit: int = 200,
        **kwargs: Any,
    ) -> list[dict[str, Any]] | dict[str, Any]:
        """Fetch market data from the market data service."""
        client = await self._ensure_connected()
        params: dict[str, Any] = {
            "symbol": symbol,
            "timeframe": timeframe,
            "type": data_type,
            "limit": limit,
            **kwargs,
        }

        try:
            response = await client.get("/market-data", params=params)
            response.raise_for_status()
            data = cast(list[dict[str, Any]] | dict[str, Any], response.json())
            logger.debug(
                "Fetched %s data for %s: %d records", data_type, symbol, len(data) if isinstance(data, list) else 1
            )
            return data
        except httpx.HTTPStatusError as exc:
            logger.error("Market data request failed (%d): %s", exc.response.status_code, exc)
            raise
        except httpx.RequestError as exc:
            logger.error("Market data request error: %s", exc)
            raise

    async def subscribe_realtime(
        self,
        symbol: str,
        channel: str = "quotes",
        callback: Callable[..., Any] | None = None,
    ) -> str:
        """Subscribe to real-time streaming data via WebSocket.

        Legacy method maintained for backward compatibility.
        Prefer ``connect_websocket()`` + ``subscribe_quotes()`` for new code.
        """
        try:
            import websockets
        except ImportError:
            raise ImportError("The 'websockets' package is required for real-time subscriptions")

        sub_key = f"{channel}:{symbol}"
        if callback:
            self._callbacks.setdefault(f"{channel.upper()}_UPDATE", callback)
            self._active_subscriptions[sub_key] = symbol

        ws_endpoint = f"{self._ws_url}/{channel}?symbol={symbol}&tenant_id={self._tenant_id}"

        try:
            ws = await websockets.connect(ws_endpoint)
            logger.info("Subscribed to %s for %s", channel, symbol)
            self._ws_task = asyncio.create_task(self._ws_listener(sub_key, ws))
        except Exception as exc:
            logger.error("WebSocket connection failed for %s: %s", sub_key, exc)
            raise

        return sub_key

    async def _ws_listener(self, sub_key: str, ws: Any) -> None:
        """Background task that listens to a WebSocket and dispatches messages."""
        try:
            async for message in ws:
                data = json.loads(message) if isinstance(message, str) else message
                msg_type = data.get("type", "") if isinstance(data, dict) else ""
                callback = self._callbacks.get(msg_type)
                if callback:
                    await callback(data)
        except Exception as exc:
            logger.warning("WebSocket listener for '%s' ended: %s", sub_key, exc)

    async def submit_order(self, order_data: dict[str, Any]) -> dict[str, Any]:
        """Submit an order to the execution service."""
        client = await self._ensure_connected()

        try:
            response = await client.post("/orders", json=order_data)
            response.raise_for_status()
            result = cast(dict[str, Any], response.json())
            logger.info("Order submitted: %s", result.get("order_id", "unknown"))
            return result
        except httpx.HTTPStatusError as exc:
            logger.error("Order submission failed (%d): %s", exc.response.status_code, exc)
            raise
        except httpx.RequestError as exc:
            logger.error("Order submission error: %s", exc)
            raise

    async def get_portfolio(
        self,
        account_id: str | None = None,
    ) -> dict[str, Any]:
        """Fetch portfolio positions and summary."""
        client = await self._ensure_connected()
        params: dict[str, str] = {}
        if account_id:
            params["account_id"] = account_id

        try:
            response = await client.get("/portfolio", params=params)
            response.raise_for_status()
            return cast(dict[str, Any], response.json())
        except httpx.HTTPStatusError as exc:
            logger.error("Portfolio request failed (%d): %s", exc.response.status_code, exc)
            raise

    async def run_backtest(self, config: dict[str, Any]) -> dict[str, Any]:
        """Submit a backtest run to the research service."""
        client = await self._ensure_connected()

        try:
            response = await client.post("/research/backtest", json=config)
            response.raise_for_status()
            result = cast(dict[str, Any], response.json())
            logger.info("Backtest submitted: %s", result.get("backtest_id", "unknown"))
            return result
        except httpx.HTTPStatusError as exc:
            logger.error("Backtest submission failed (%d): %s", exc.response.status_code, exc)
            raise

    async def __aenter__(self) -> DataClient:
        await self.connect()
        return self

    async def __aexit__(self, *args: Any) -> None:
        await self.disconnect()


__all__ = [
    "DataClient",
]
