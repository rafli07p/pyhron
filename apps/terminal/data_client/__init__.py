"""Data Client for the Enthropy Terminal.

HTTP and WebSocket client that consumes the services/api layer. Provides
methods for fetching market data, subscribing to real-time streams,
submitting orders, querying portfolios, and running backtests.

Uses ``httpx`` for HTTP requests and ``websockets`` for real-time
streaming connections.
"""

from __future__ import annotations

import asyncio
import json
import logging
from collections.abc import Callable
from typing import Any, cast
from urllib.parse import urljoin

import httpx

logger = logging.getLogger(__name__)

# Default API base URL for the Enthropy services API
_DEFAULT_BASE_URL = "http://localhost:8000/api/v1"
_DEFAULT_WS_URL = "ws://localhost:8000/ws"


class DataClient:
    """HTTP/WebSocket client for consuming Enthropy services.

    Provides a unified interface for the terminal to interact with all
    backend services including market data, execution, portfolio, and
    research APIs.

    Parameters
    ----------
    base_url:
        HTTP base URL for the services API.
    ws_url:
        WebSocket URL for real-time streaming.
    api_key:
        API key for authentication.
    tenant_id:
        Tenant identifier for multi-tenant requests.
    timeout:
        HTTP request timeout in seconds.
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
        self._ws_connections: dict[str, Any] = {}
        self._subscriptions: dict[str, Callable[..., Any]] = {}
        logger.info("DataClient initialized (base_url=%s, tenant_id=%s)", base_url, tenant_id)

    @property
    def is_connected(self) -> bool:
        """Whether the HTTP client is initialized."""
        return self._http_client is not None and not self._http_client.is_closed

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
        if self._http_client and not self._http_client.is_closed:
            await self._http_client.aclose()
            logger.info("HTTP client disconnected")

        for channel, ws in self._ws_connections.items():
            try:
                await ws.close()
            except Exception:
                pass
            logger.info("WebSocket closed for channel '%s'", channel)
        self._ws_connections.clear()
        self._subscriptions.clear()

    async def _ensure_connected(self) -> httpx.AsyncClient:
        """Ensure the HTTP client is connected and return it."""
        if not self.is_connected:
            await self.connect()
        assert self._http_client is not None
        return self._http_client

    async def get_market_data(
        self,
        symbol: str,
        timeframe: str = "1D",
        data_type: str = "bars",
        limit: int = 200,
        **kwargs: Any,
    ) -> list[dict[str, Any]] | dict[str, Any]:
        """Fetch market data from the market data service.

        Parameters
        ----------
        symbol:
            Instrument symbol.
        timeframe:
            Bar interval (e.g., ``1m``, ``5m``, ``1D``).
        data_type:
            Type of data to fetch (``bars``, ``quotes``, ``orderbook``,
            ``news``, ``datasets``, ``factor_analysis``).
        limit:
            Maximum number of records to return.
        **kwargs:
            Additional query parameters.

        Returns
        -------
        list[dict[str, Any]] | dict[str, Any]
            Market data response.
        """
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
            logger.debug("Fetched %s data for %s: %d records", data_type, symbol, len(data) if isinstance(data, list) else 1)
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

        Parameters
        ----------
        symbol:
            Instrument symbol to subscribe to.
        channel:
            Data channel (``quotes``, ``trades``, ``orderbook``).
        callback:
            Async callable invoked with each incoming message.

        Returns
        -------
        str
            Subscription key for managing the subscription.
        """
        try:
            import websockets
        except ImportError:
            logger.warning("websockets package not installed; real-time subscriptions unavailable")
            raise ImportError("The 'websockets' package is required for real-time subscriptions")

        sub_key = f"{channel}:{symbol}"
        if callback:
            self._subscriptions[sub_key] = callback

        ws_endpoint = f"{self._ws_url}/{channel}?symbol={symbol}&tenant_id={self._tenant_id}"

        try:
            ws = await websockets.connect(ws_endpoint)
            self._ws_connections[sub_key] = ws
            logger.info("Subscribed to %s for %s", channel, symbol)

            # Start background listener
            asyncio.create_task(self._ws_listener(sub_key, ws))
        except Exception as exc:
            logger.error("WebSocket connection failed for %s: %s", sub_key, exc)
            raise

        return sub_key

    async def _ws_listener(self, sub_key: str, ws: Any) -> None:
        """Background task that listens to a WebSocket and dispatches messages."""
        try:
            async for message in ws:
                data = json.loads(message) if isinstance(message, str) else message
                callback = self._subscriptions.get(sub_key)
                if callback:
                    await callback(data)
        except Exception as exc:
            logger.warning("WebSocket listener for '%s' ended: %s", sub_key, exc)
        finally:
            self._ws_connections.pop(sub_key, None)

    async def submit_order(self, order_data: dict[str, Any]) -> dict[str, Any]:
        """Submit an order to the execution service.

        Parameters
        ----------
        order_data:
            Order payload (serialized ``OrderRequest`` or cancel action).

        Returns
        -------
        dict[str, Any]
            Order submission response with order ID and status.
        """
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
        """Fetch portfolio positions and summary.

        Parameters
        ----------
        account_id:
            Optional account identifier. If ``None``, returns the
            default account portfolio.

        Returns
        -------
        dict[str, Any]
            Portfolio data with positions, P&L, and exposure.
        """
        client = await self._ensure_connected()
        params: dict[str, str] = {}
        if account_id:
            params["account_id"] = account_id

        try:
            response = await client.get("/portfolio", params=params)
            response.raise_for_status()
            portfolio_data = cast(dict[str, Any], response.json())
            return portfolio_data
        except httpx.HTTPStatusError as exc:
            logger.error("Portfolio request failed (%d): %s", exc.response.status_code, exc)
            raise

    async def run_backtest(self, config: dict[str, Any]) -> dict[str, Any]:
        """Submit a backtest run to the research service.

        Parameters
        ----------
        config:
            Backtest configuration dictionary with strategy name,
            date range, symbols, and parameters.

        Returns
        -------
        dict[str, Any]
            Backtest submission result with ID and initial status.
        """
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
        """Async context manager entry."""
        await self.connect()
        return self

    async def __aexit__(self, *args: Any) -> None:
        """Async context manager exit."""
        await self.disconnect()


__all__ = [
    "DataClient",
]
