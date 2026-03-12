"""Async data client for the Pyhron terminal.

Wraps HTTP and WebSocket connections to the Pyhron API with
reconnection, backoff, caching, and offline fallback.
"""

from __future__ import annotations

import asyncio
import json
import time
from collections.abc import Callable
from decimal import Decimal
from pathlib import Path
from typing import Any

import httpx

from shared.structured_json_logger import get_logger

logger = get_logger(__name__)

_CACHE_DIR = Path.home() / ".pyhron" / "cache"
_STALE_QUOTE_SECONDS = 60
_STALE_POSITION_SECONDS = 30
_MAX_RECONNECT_BACKOFF = 60
_DEGRADED_THRESHOLD = 3


class PyhronDataClient:
    """Async data client for the terminal.

    Manages HTTP and WebSocket connections to the Pyhron API.
    Handles reconnection, backoff, and offline fallback.
    """

    def __init__(self, base_url: str, jwt_token: str) -> None:
        self._base_url = base_url.rstrip("/")
        self._token = jwt_token
        self._client: httpx.AsyncClient | None = None
        self._ws_task: asyncio.Task[None] | None = None
        self._consecutive_failures = 0
        self._degraded = False
        self._quote_callbacks: list[Callable[..., Any]] = []
        self._order_callbacks: list[Callable[..., Any]] = []
        self._last_fetch: dict[str, float] = {}
        _CACHE_DIR.mkdir(parents=True, exist_ok=True)

    @property
    def is_degraded(self) -> bool:
        return self._degraded

    async def connect(self) -> None:
        """Initialise the HTTP client."""
        self._client = httpx.AsyncClient(
            base_url=self._base_url,
            headers={"Authorization": f"Bearer {self._token}"},
            timeout=10,
        )

    async def disconnect(self) -> None:
        """Close all connections."""
        if self._ws_task and not self._ws_task.done():
            self._ws_task.cancel()
        if self._client:
            await self._client.aclose()
            self._client = None

    async def _get(self, path: str, params: dict[str, Any] | None = None) -> Any:
        """Make an authenticated GET request with failure tracking."""
        if not self._client:
            await self.connect()
        assert self._client is not None

        try:
            resp = await self._client.get(path, params=params)
            resp.raise_for_status()
            self._consecutive_failures = 0
            if self._degraded:
                self._degraded = False
                logger.info("connection_restored")
            data = resp.json()
            self._last_fetch[path] = time.monotonic()
            return data
        except (httpx.HTTPError, httpx.ConnectError) as exc:
            self._consecutive_failures += 1
            if self._consecutive_failures >= _DEGRADED_THRESHOLD:
                self._degraded = True
                logger.warning("degraded_mode_activated", failures=self._consecutive_failures)
            logger.warning("api_request_failed", path=path, error=str(exc))
            return self._load_cache(path)

    async def _post(self, path: str, payload: dict[str, Any]) -> Any:
        """Make an authenticated POST request."""
        if self._degraded:
            return {"error": "Offline mode — order submission disabled"}
        if not self._client:
            await self.connect()
        assert self._client is not None

        resp = await self._client.post(path, json=payload)
        resp.raise_for_status()
        self._consecutive_failures = 0
        return resp.json()

    def _load_cache(self, key: str) -> Any:
        """Load cached response for a path."""
        safe_key = key.replace("/", "_").strip("_")
        cache_file = _CACHE_DIR / f"{safe_key}.json"
        if cache_file.exists():
            return json.loads(cache_file.read_text())
        return None

    def _save_cache(self, key: str, data: Any) -> None:
        """Save response to disk cache."""
        safe_key = key.replace("/", "_").strip("_")
        cache_file = _CACHE_DIR / f"{safe_key}.json"
        cache_file.write_text(json.dumps(data, default=str))

    async def get_quote(self, symbol: str) -> dict[str, Any] | None:
        """Fetch latest quote for a symbol."""
        data = await self._get(f"/api/v1/market-data/{symbol}", {"interval": "1min", "limit": "1"})
        if data:
            self._save_cache(f"quote_{symbol}", data)
        result: dict[str, Any] | None = data
        return result

    async def get_ohlcv(self, symbol: str, timeframe: str = "1day", n_bars: int = 60) -> Any:
        """Fetch OHLCV data."""
        return await self._get(
            f"/api/v1/market-data/{symbol}",
            {"interval": timeframe, "limit": str(n_bars)},
        )

    async def get_positions(self) -> Any:
        """Fetch current portfolio positions."""
        data = await self._get("/api/v1/portfolio")
        if data:
            self._save_cache("portfolio", data)
        return data

    async def get_orders_today(self) -> Any:
        """Fetch today's orders."""
        data = await self._get("/api/v1/orders", {"limit": "100"})
        if data:
            self._save_cache("orders_today", data)
        return data

    async def submit_order(
        self,
        symbol: str,
        side: str,
        order_type: str,
        quantity_lots: int,
        limit_price: Decimal | None,
    ) -> Any:
        """Submit a new order."""
        payload: dict[str, Any] = {
            "symbol": symbol,
            "side": side,
            "order_type": order_type,
            "qty": quantity_lots * 100,  # lots to shares
        }
        if limit_price is not None:
            payload["price"] = str(limit_price)
        return await self._post("/api/v1/orders", payload)

    async def cancel_order(self, order_id: str) -> Any:
        """Cancel an open order."""
        if self._degraded:
            return {"error": "Offline mode — cannot cancel orders"}
        if not self._client:
            await self.connect()
        assert self._client is not None
        resp = await self._client.delete(f"/api/v1/orders/{order_id}")
        resp.raise_for_status()
        return resp.json()

    async def get_momentum_signals(self) -> Any:
        """Fetch momentum strategy signals."""
        return await self._get("/api/v1/research/momentum-signals")

    async def get_instrument_universe(self) -> Any:
        """Fetch instrument universe."""
        return await self._get("/api/v1/instruments")

    async def subscribe_quotes(
        self,
        symbols: list[str],
        callback: Callable[..., Any],
    ) -> None:
        """Subscribe to real-time quote updates via WebSocket."""
        self._quote_callbacks.append(callback)
        if self._ws_task is None or self._ws_task.done():
            self._ws_task = asyncio.create_task(self._ws_loop(symbols))

    async def subscribe_order_updates(
        self,
        callback: Callable[..., Any],
    ) -> None:
        """Register callback for order status updates."""
        self._order_callbacks.append(callback)

    async def _ws_loop(self, symbols: list[str]) -> None:
        """WebSocket reconnection loop with exponential backoff."""
        import websockets

        backoff = 1.0
        ws_url = self._base_url.replace("http", "ws", 1) + f"/ws/market-data?token={self._token}"

        while True:
            try:
                async with websockets.connect(ws_url) as ws:
                    backoff = 1.0
                    # Subscribe to symbols
                    for sym in symbols:
                        await ws.send(json.dumps({"type": "subscribe", "symbol": sym}))

                    async for raw in ws:
                        msg = json.loads(raw)
                        for cb in self._quote_callbacks:
                            try:
                                cb(msg)
                            except Exception:
                                logger.exception("quote_callback_error")

            except Exception:
                logger.warning("ws_disconnected", backoff=backoff)
                await asyncio.sleep(backoff)
                backoff = min(backoff * 2, _MAX_RECONNECT_BACKOFF)
