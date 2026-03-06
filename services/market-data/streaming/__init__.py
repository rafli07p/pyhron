"""Real-time market data streaming service.

Uses Polygon.io WebSocket for live US equity / options / crypto feeds.
Distributes received events internally via Redis pub/sub and exposes an
async callback-based API for consumers.
"""

from __future__ import annotations

import asyncio
import json
import os
from datetime import datetime
from decimal import Decimal
from typing import Any, Callable, Coroutine, Optional, Sequence

import redis.asyncio as aioredis
import structlog
from dotenv import load_dotenv
from polygon import WebSocketClient
from polygon.websocket.models import WebSocketMessage
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from shared.schemas.market_events import (
    BarEvent,
    Exchange,
    QuoteEvent,
    TradeEvent,
)

load_dotenv()

logger = structlog.get_logger(__name__)

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
_POLYGON_API_KEY = os.getenv("POLYGON_API_KEY", "")
_REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
_WS_MAX_RECONNECT_ATTEMPTS = int(os.getenv("WS_MAX_RECONNECT_ATTEMPTS", "10"))
_WS_RECONNECT_BASE_DELAY = float(os.getenv("WS_RECONNECT_BASE_DELAY", "1.0"))
_WS_RECONNECT_MAX_DELAY = float(os.getenv("WS_RECONNECT_MAX_DELAY", "60.0"))
_CONNECTION_POOL_SIZE = int(os.getenv("WS_CONNECTION_POOL_SIZE", "5"))
_RATE_LIMIT_MESSAGES_PER_SECOND = int(os.getenv("WS_RATE_LIMIT_MPS", "1000"))

# Callback type alias
MessageCallback = Callable[[BarEvent | TradeEvent | QuoteEvent], Coroutine[Any, Any, None]]


class StreamingService:
    """Async WebSocket streaming service for real-time market data.

    Parameters
    ----------
    tenant_id:
        Tenant identifier for multi-tenancy isolation.
    polygon_api_key:
        Polygon.io API key.  Falls back to ``POLYGON_API_KEY`` env var.
    redis_url:
        Redis URL for internal pub/sub distribution.
    """

    def __init__(
        self,
        tenant_id: str,
        polygon_api_key: Optional[str] = None,
        redis_url: Optional[str] = None,
    ) -> None:
        self.tenant_id = tenant_id
        self._polygon_key = polygon_api_key or _POLYGON_API_KEY
        self._redis_url = redis_url or _REDIS_URL

        # WebSocket state
        self._ws_client: Optional[WebSocketClient] = None
        self._ws_task: Optional[asyncio.Task[None]] = None
        self._connected = False
        self._subscribed_symbols: list[str] = []

        # Redis pub/sub
        self._redis: Optional[aioredis.Redis] = None
        self._pubsub_channel = f"mkt:realtime:{tenant_id}"

        # Callbacks
        self._callbacks: list[MessageCallback] = []

        # Rate limiting
        self._msg_count = 0
        self._msg_window_start: float = 0.0

        # Reconnection state
        self._reconnect_attempts = 0
        self._should_reconnect = True

        self._log = logger.bind(tenant_id=tenant_id, service="streaming")

    # ------------------------------------------------------------------
    # Redis helpers
    # ------------------------------------------------------------------

    async def _get_redis(self) -> aioredis.Redis:
        if self._redis is None:
            self._redis = aioredis.from_url(
                self._redis_url,
                decode_responses=True,
                max_connections=_CONNECTION_POOL_SIZE,
            )
        return self._redis

    async def _publish_to_redis(self, event: BarEvent | TradeEvent | QuoteEvent) -> None:
        """Publish a normalised event to Redis pub/sub."""
        r = await self._get_redis()
        payload = event.model_dump_json()
        await r.publish(self._pubsub_channel, payload)

    # ------------------------------------------------------------------
    # Rate limiting
    # ------------------------------------------------------------------

    def _check_rate_limit(self) -> bool:
        """Return ``True`` if the current message is within rate limits."""
        now = asyncio.get_event_loop().time()
        if now - self._msg_window_start > 1.0:
            self._msg_count = 0
            self._msg_window_start = now
        self._msg_count += 1
        return self._msg_count <= _RATE_LIMIT_MESSAGES_PER_SECOND

    # ------------------------------------------------------------------
    # Connection management
    # ------------------------------------------------------------------

    async def connect(self) -> None:
        """Establish WebSocket connection to Polygon.io.

        Creates the ``WebSocketClient`` but does not subscribe to any
        symbols yet -- call :meth:`subscribe` after connecting.
        """
        if self._connected:
            self._log.warning("already_connected")
            return

        if not self._polygon_key:
            raise RuntimeError(
                "POLYGON_API_KEY is not set. Provide via constructor or env var."
            )

        self._ws_client = WebSocketClient(
            api_key=self._polygon_key,
            subscriptions=[],
        )
        self._connected = True
        self._should_reconnect = True
        self._reconnect_attempts = 0
        self._log.info("ws_connected")

    async def subscribe(
        self,
        symbols: Sequence[str],
        channels: Optional[Sequence[str]] = None,
    ) -> None:
        """Subscribe to real-time data for *symbols*.

        Parameters
        ----------
        symbols:
            Ticker symbols to subscribe to (e.g. ``["AAPL", "MSFT"]``).
        channels:
            Polygon channel prefixes.  Defaults to ``["T", "Q", "AM"]``
            (trades, quotes, aggregate-minute bars).
        """
        if not self._connected or self._ws_client is None:
            raise RuntimeError("Not connected. Call connect() first.")

        ch = channels or ["T", "Q", "AM"]
        subs: list[str] = []
        for symbol in symbols:
            for prefix in ch:
                subs.append(f"{prefix}.{symbol}")

        self._subscribed_symbols = list(symbols)

        # Start the WebSocket listener in a background task
        if self._ws_task is None or self._ws_task.done():
            self._ws_task = asyncio.create_task(self._ws_listen_loop(subs))

        self._log.info(
            "subscribed",
            symbols=list(symbols),
            channels=list(ch),
            subscription_count=len(subs),
        )

    def on_message(self, callback: MessageCallback) -> MessageCallback:
        """Register an async callback for incoming market events.

        Can be used as a decorator::

            @streamer.on_message
            async def handle(event):
                ...
        """
        self._callbacks.append(callback)
        return callback

    # ------------------------------------------------------------------
    # WebSocket listener
    # ------------------------------------------------------------------

    async def _ws_listen_loop(self, subscriptions: list[str]) -> None:
        """Main WebSocket loop with automatic reconnection."""
        while self._should_reconnect:
            try:
                await self._run_ws(subscriptions)
            except Exception:
                self._reconnect_attempts += 1
                if self._reconnect_attempts > _WS_MAX_RECONNECT_ATTEMPTS:
                    self._log.error(
                        "ws_max_reconnect_exceeded",
                        attempts=self._reconnect_attempts,
                    )
                    self._connected = False
                    return

                delay = min(
                    _WS_RECONNECT_BASE_DELAY * (2 ** (self._reconnect_attempts - 1)),
                    _WS_RECONNECT_MAX_DELAY,
                )
                self._log.warning(
                    "ws_reconnecting",
                    attempt=self._reconnect_attempts,
                    delay=delay,
                    exc_info=True,
                )
                await asyncio.sleep(delay)

    async def _run_ws(self, subscriptions: list[str]) -> None:
        """Run a single WebSocket session.

        The ``polygon`` client's ``WebSocketClient.run()`` is blocking,
        so we execute it in a thread executor to keep the event loop free.
        """
        if self._ws_client is None:
            return

        # Reconfigure client with current subscriptions
        self._ws_client = WebSocketClient(
            api_key=self._polygon_key,
            subscriptions=subscriptions,
        )

        loop = asyncio.get_running_loop()

        def _handle_msgs(msgs: list[WebSocketMessage]) -> None:
            """Synchronous handler invoked by Polygon WS client."""
            for msg in msgs:
                if not self._check_rate_limit():
                    continue
                try:
                    event = self._parse_ws_message(msg)
                    if event is not None:
                        # Schedule async work from sync callback
                        asyncio.run_coroutine_threadsafe(
                            self._dispatch_event(event), loop
                        )
                except Exception:
                    self._log.warning("ws_message_parse_error", exc_info=True)

        self._ws_client.run(handle_msg=_handle_msgs)
        self._reconnect_attempts = 0

    def _parse_ws_message(
        self, msg: WebSocketMessage
    ) -> BarEvent | TradeEvent | QuoteEvent | None:
        """Convert a Polygon WebSocket message into an Enthropy event."""
        event_type = getattr(msg, "event_type", None) or getattr(msg, "ev", None)

        if event_type in ("AM", "A"):
            # Aggregate bar
            return BarEvent(
                symbol=getattr(msg, "symbol", getattr(msg, "sym", "")),
                timestamp=datetime.utcfromtimestamp(
                    getattr(msg, "end_timestamp", 0) / 1000
                ),
                exchange=Exchange.OTHER,
                tenant_id=self.tenant_id,
                open=Decimal(str(getattr(msg, "open", 0))),
                high=Decimal(str(getattr(msg, "high", 0))),
                low=Decimal(str(getattr(msg, "low", 0))),
                close=Decimal(str(getattr(msg, "close", 0))),
                volume=Decimal(str(getattr(msg, "volume", 0))),
                vwap=Decimal(str(msg.vwap)) if getattr(msg, "vwap", None) else None,
                interval_seconds=60,
            )

        if event_type == "T":
            # Trade
            return TradeEvent(
                symbol=getattr(msg, "symbol", getattr(msg, "sym", "")),
                timestamp=datetime.utcfromtimestamp(
                    getattr(msg, "timestamp", 0) / 1e9
                ),
                exchange=Exchange.OTHER,
                tenant_id=self.tenant_id,
                price=Decimal(str(getattr(msg, "price", 0))),
                volume=Decimal(str(getattr(msg, "size", 0))),
                trade_id=str(getattr(msg, "id", "")),
            )

        if event_type == "Q":
            # Quote
            return QuoteEvent(
                symbol=getattr(msg, "symbol", getattr(msg, "sym", "")),
                timestamp=datetime.utcfromtimestamp(
                    getattr(msg, "timestamp", 0) / 1e9
                ),
                exchange=Exchange.OTHER,
                tenant_id=self.tenant_id,
                bid=Decimal(str(getattr(msg, "bid_price", 0))),
                ask=Decimal(str(getattr(msg, "ask_price", 0))),
                bid_size=Decimal(str(getattr(msg, "bid_size", 0))),
                ask_size=Decimal(str(getattr(msg, "ask_size", 0))),
            )

        return None

    async def _dispatch_event(
        self, event: BarEvent | TradeEvent | QuoteEvent
    ) -> None:
        """Send event to all registered callbacks and Redis pub/sub."""
        # Publish to Redis for other services
        try:
            await self._publish_to_redis(event)
        except Exception:
            self._log.warning("redis_publish_failed", exc_info=True)

        # Invoke registered callbacks
        for cb in self._callbacks:
            try:
                await cb(event)
            except Exception:
                self._log.warning("callback_error", exc_info=True)

    # ------------------------------------------------------------------
    # Disconnect
    # ------------------------------------------------------------------

    async def disconnect(self) -> None:
        """Gracefully disconnect the WebSocket and release resources."""
        self._should_reconnect = False
        self._connected = False

        if self._ws_task is not None:
            self._ws_task.cancel()
            try:
                await self._ws_task
            except asyncio.CancelledError:
                pass
            self._ws_task = None

        if self._redis is not None:
            await self._redis.aclose()
            self._redis = None

        self._ws_client = None
        self._callbacks.clear()
        self._subscribed_symbols.clear()
        self._log.info("ws_disconnected")

    # ------------------------------------------------------------------
    # Redis subscriber (consumer side)
    # ------------------------------------------------------------------

    async def listen_redis(
        self,
        callback: MessageCallback,
        channel: Optional[str] = None,
    ) -> None:
        """Subscribe to the Redis pub/sub channel and forward events.

        This is the consumer-side counterpart -- other services call this
        to receive events that were published by the WebSocket listener.

        Parameters
        ----------
        callback:
            Async function called with each deserialised event.
        channel:
            Override the default ``mkt:realtime:{tenant_id}`` channel.
        """
        r = await self._get_redis()
        pubsub = r.pubsub()
        ch = channel or self._pubsub_channel
        await pubsub.subscribe(ch)
        self._log.info("redis_listener_started", channel=ch)

        try:
            async for message in pubsub.listen():
                if message["type"] != "message":
                    continue
                data = json.loads(message["data"])
                # Determine event type from fields
                if "open" in data and "high" in data:
                    event = BarEvent.model_validate(data)
                elif "bid" in data and "ask" in data:
                    event = QuoteEvent.model_validate(data)
                else:
                    event = TradeEvent.model_validate(data)
                await callback(event)
        finally:
            await pubsub.unsubscribe(ch)

    # ------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------

    @property
    def is_connected(self) -> bool:
        return self._connected

    @property
    def subscribed_symbols(self) -> list[str]:
        return list(self._subscribed_symbols)


__all__ = ["StreamingService", "MessageCallback"]
