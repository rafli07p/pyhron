"""Alpaca broker adapter for US equity trading.

Implements the BrokerAdapter interface using Alpaca's REST API (v2) and
WebSocket streaming for real-time trade updates.

Requires ALPACA_API_KEY, ALPACA_SECRET_KEY, and ALPACA_BASE_URL in config.
"""

from __future__ import annotations

import json
from typing import AsyncIterator

import httpx
import websockets

from services.broker.base import BrokerAdapter
from shared.configuration_settings import get_config
from shared.platform_exception_hierarchy import BrokerConnectionError, BrokerTimeoutError, OrderRejectedError
from shared.structured_json_logger import get_logger
from shared.proto_generated.equity_orders_pb2 import OrderRequest

logger = get_logger(__name__)

# Alpaca WebSocket URL for trade updates (paper trading)
ALPACA_WS_URL = "wss://paper-api.alpaca.markets/stream"
ALPACA_DATA_WS_URL = "wss://stream.data.alpaca.markets/v2/iex"

# HTTP timeout in seconds
HTTP_TIMEOUT = 30.0

# Map proto OrderSide to Alpaca side strings
_SIDE_MAP = {
    1: "buy",   # ORDER_SIDE_BUY
    2: "sell",  # ORDER_SIDE_SELL
}

# Map proto OrderType to Alpaca type strings
_ORDER_TYPE_MAP = {
    1: "market",      # ORDER_TYPE_MARKET
    2: "limit",       # ORDER_TYPE_LIMIT
    3: "stop",        # ORDER_TYPE_STOP
    4: "stop_limit",  # ORDER_TYPE_STOP_LIMIT
}

# Map proto TimeInForce to Alpaca TIF strings
_TIF_MAP = {
    1: "day",  # TIME_IN_FORCE_DAY
    2: "gtc",  # TIME_IN_FORCE_GTC
    3: "ioc",  # TIME_IN_FORCE_IOC
    4: "fok",  # TIME_IN_FORCE_FOK
}


class AlpacaAdapter(BrokerAdapter):
    """Alpaca broker adapter using REST API v2 and WebSocket streaming.

    Authenticates with API key and secret key via HTTP headers.
    All REST calls go through httpx.AsyncClient for non-blocking I/O.

    Usage::

        adapter = AlpacaAdapter()
        broker_id = await adapter.submit_order(order_request)
        positions = await adapter.get_positions()

        async for fill in adapter.stream_fills():
            print(fill)
    """

    def __init__(self) -> None:
        config = get_config()
        self._api_key = config.alpaca_api_key
        self._secret_key = config.alpaca_secret_key
        self._base_url = config.alpaca_base_url.rstrip("/")
        self._headers = {
            "APCA-API-KEY-ID": self._api_key,
            "APCA-API-SECRET-KEY": self._secret_key,
            "Content-Type": "application/json",
        }
        self._client: httpx.AsyncClient | None = None

    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create the shared HTTP client.

        Returns:
            An httpx.AsyncClient configured with Alpaca auth headers.
        """
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                base_url=self._base_url,
                headers=self._headers,
                timeout=HTTP_TIMEOUT,
            )
        return self._client

    async def close(self) -> None:
        """Close the underlying HTTP client."""
        if self._client is not None and not self._client.is_closed:
            await self._client.aclose()
            self._client = None

    async def submit_order(self, order: OrderRequest) -> str:
        """Submit an order to Alpaca via POST /v2/orders.

        Args:
            order: The OrderRequest protobuf with order details.

        Returns:
            The Alpaca-assigned order ID.

        Raises:
            OrderRejectedError: If Alpaca returns 403 or 422 (order rejected).
            BrokerConnectionError: If connection to Alpaca fails.
            BrokerTimeoutError: If the request times out.
        """
        client = await self._get_client()

        payload: dict[str, object] = {
            "symbol": order.symbol,
            "qty": str(order.quantity),
            "side": _SIDE_MAP.get(order.side, "buy"),
            "type": _ORDER_TYPE_MAP.get(order.order_type, "market"),
            "time_in_force": _TIF_MAP.get(order.time_in_force, "day"),
            "client_order_id": order.client_order_id,
        }

        # Add price fields for limit/stop orders
        if order.order_type in (2, 4) and order.limit_price > 0:
            payload["limit_price"] = str(order.limit_price)
        if order.order_type in (3, 4) and order.stop_price > 0:
            payload["stop_price"] = str(order.stop_price)

        try:
            response = await client.post("/v2/orders", json=payload)
        except httpx.TimeoutException as exc:
            raise BrokerTimeoutError(
                f"Alpaca order submission timed out for {order.symbol}: {exc}"
            ) from exc
        except httpx.HTTPError as exc:
            raise BrokerConnectionError(
                f"Failed to connect to Alpaca for order submission: {exc}"
            ) from exc

        if response.status_code in (403, 422):
            body = response.json()
            raise OrderRejectedError(
                f"Alpaca rejected order for {order.symbol}: {body.get('message', '')}",
                broker_order_id="",
                reason=body.get("message", str(body)),
            )

        if response.status_code >= 400:
            raise BrokerConnectionError(
                f"Alpaca returned HTTP {response.status_code}: {response.text}"
            )

        data = response.json()
        broker_order_id = data["id"]

        logger.info(
            "alpaca_order_submitted",
            broker_order_id=broker_order_id,
            symbol=order.symbol,
            side=payload["side"],
            qty=order.quantity,
        )

        return broker_order_id

    async def cancel_order(self, broker_order_id: str) -> bool:
        """Cancel an order via DELETE /v2/orders/{id}.

        Args:
            broker_order_id: The Alpaca-assigned order ID.

        Returns:
            True if cancellation was accepted (HTTP 204), False otherwise.

        Raises:
            BrokerConnectionError: If connection to Alpaca fails.
            BrokerTimeoutError: If the request times out.
        """
        client = await self._get_client()

        try:
            response = await client.delete(f"/v2/orders/{broker_order_id}")
        except httpx.TimeoutException as exc:
            raise BrokerTimeoutError(
                f"Alpaca cancel timed out for {broker_order_id}: {exc}"
            ) from exc
        except httpx.HTTPError as exc:
            raise BrokerConnectionError(
                f"Failed to connect to Alpaca for cancel: {exc}"
            ) from exc

        if response.status_code == 204:
            logger.info("alpaca_order_cancelled", broker_order_id=broker_order_id)
            return True

        if response.status_code == 404:
            logger.warning(
                "alpaca_cancel_not_found",
                broker_order_id=broker_order_id,
            )
            return False

        if response.status_code == 422:
            logger.warning(
                "alpaca_cancel_not_cancellable",
                broker_order_id=broker_order_id,
                response=response.text,
            )
            return False

        if response.status_code >= 400:
            raise BrokerConnectionError(
                f"Alpaca cancel returned HTTP {response.status_code}: {response.text}"
            )

        return True

    async def get_order_status(self, broker_order_id: str) -> dict:
        """Get order status via GET /v2/orders/{id}.

        Args:
            broker_order_id: The Alpaca-assigned order ID.

        Returns:
            Dict with status, filled_qty, avg_fill_price, and broker_order_id.

        Raises:
            BrokerConnectionError: If connection to Alpaca fails.
            BrokerTimeoutError: If the request times out.
        """
        client = await self._get_client()

        try:
            response = await client.get(f"/v2/orders/{broker_order_id}")
        except httpx.TimeoutException as exc:
            raise BrokerTimeoutError(
                f"Alpaca get_order_status timed out for {broker_order_id}: {exc}"
            ) from exc
        except httpx.HTTPError as exc:
            raise BrokerConnectionError(
                f"Failed to connect to Alpaca for order status: {exc}"
            ) from exc

        if response.status_code >= 400:
            raise BrokerConnectionError(
                f"Alpaca order status returned HTTP {response.status_code}: {response.text}"
            )

        data = response.json()

        return {
            "broker_order_id": data.get("id", broker_order_id),
            "client_order_id": data.get("client_order_id", ""),
            "status": data.get("status", "unknown"),
            "filled_qty": int(data.get("filled_qty", 0) or 0),
            "avg_fill_price": float(data.get("filled_avg_price", 0) or 0),
            "symbol": data.get("symbol", ""),
            "side": data.get("side", ""),
            "qty": int(data.get("qty", 0) or 0),
            "order_type": data.get("type", ""),
            "created_at": data.get("created_at", ""),
            "updated_at": data.get("updated_at", ""),
        }

    async def get_positions(self) -> list[dict]:
        """Fetch all positions via GET /v2/positions.

        Returns:
            List of position dicts with symbol, qty, market_value, avg_entry_price.

        Raises:
            BrokerConnectionError: If connection to Alpaca fails.
        """
        client = await self._get_client()

        try:
            response = await client.get("/v2/positions")
        except httpx.TimeoutException as exc:
            raise BrokerTimeoutError(
                f"Alpaca get_positions timed out: {exc}"
            ) from exc
        except httpx.HTTPError as exc:
            raise BrokerConnectionError(
                f"Failed to connect to Alpaca for positions: {exc}"
            ) from exc

        if response.status_code >= 400:
            raise BrokerConnectionError(
                f"Alpaca positions returned HTTP {response.status_code}: {response.text}"
            )

        data = response.json()
        positions = []

        for pos in data:
            positions.append({
                "symbol": pos.get("symbol", ""),
                "qty": int(pos.get("qty", 0) or 0),
                "market_value": float(pos.get("market_value", 0) or 0),
                "avg_entry_price": float(pos.get("avg_entry_price", 0) or 0),
                "current_price": float(pos.get("current_price", 0) or 0),
                "unrealized_pl": float(pos.get("unrealized_pl", 0) or 0),
                "unrealized_plpc": float(pos.get("unrealized_plpc", 0) or 0),
                "side": pos.get("side", "long"),
                "exchange": pos.get("exchange", ""),
            })

        logger.debug("alpaca_positions_fetched", count=len(positions))
        return positions

    async def get_account(self) -> dict:
        """Fetch account info via GET /v2/account.

        Returns:
            Dict with equity, cash, buying_power, and portfolio_value.

        Raises:
            BrokerConnectionError: If connection to Alpaca fails.
        """
        client = await self._get_client()

        try:
            response = await client.get("/v2/account")
        except httpx.TimeoutException as exc:
            raise BrokerTimeoutError(
                f"Alpaca get_account timed out: {exc}"
            ) from exc
        except httpx.HTTPError as exc:
            raise BrokerConnectionError(
                f"Failed to connect to Alpaca for account info: {exc}"
            ) from exc

        if response.status_code >= 400:
            raise BrokerConnectionError(
                f"Alpaca account returned HTTP {response.status_code}: {response.text}"
            )

        data = response.json()

        return {
            "account_id": data.get("id", ""),
            "status": data.get("status", ""),
            "equity": float(data.get("equity", 0) or 0),
            "cash": float(data.get("cash", 0) or 0),
            "buying_power": float(data.get("buying_power", 0) or 0),
            "portfolio_value": float(data.get("portfolio_value", 0) or 0),
            "long_market_value": float(data.get("long_market_value", 0) or 0),
            "short_market_value": float(data.get("short_market_value", 0) or 0),
            "pattern_day_trader": data.get("pattern_day_trader", False),
            "trading_blocked": data.get("trading_blocked", False),
            "account_blocked": data.get("account_blocked", False),
            "currency": data.get("currency", "USD"),
        }

    async def stream_fills(self) -> AsyncIterator[dict]:
        """Stream real-time trade updates via Alpaca WebSocket.

        Connects to the Alpaca streaming API, authenticates, subscribes
        to trade updates, and yields fill events as they arrive.

        Yields:
            Fill event dicts with broker_order_id, client_order_id,
            filled_qty, filled_price, commission, and event_type.

        Raises:
            BrokerConnectionError: If the WebSocket connection fails.
        """
        ws_url = self._base_url.replace("https://", "wss://").replace(
            "http://", "ws://"
        ) + "/stream"

        try:
            async for websocket in websockets.connect(ws_url):
                try:
                    # Authenticate
                    auth_msg = {
                        "action": "auth",
                        "key": self._api_key,
                        "secret": self._secret_key,
                    }
                    await websocket.send(json.dumps(auth_msg))
                    auth_response = await websocket.recv()
                    auth_data = json.loads(auth_response)

                    if isinstance(auth_data, dict) and auth_data.get("data", {}).get("status") == "unauthorized":
                        raise BrokerConnectionError(
                            "Alpaca WebSocket authentication failed"
                        )

                    # Subscribe to trade updates
                    subscribe_msg = {
                        "action": "listen",
                        "data": {
                            "streams": ["trade_updates"],
                        },
                    }
                    await websocket.send(json.dumps(subscribe_msg))

                    logger.info("alpaca_websocket_connected")

                    # Process incoming messages
                    async for raw_message in websocket:
                        message = json.loads(raw_message)
                        stream = message.get("stream", "")

                        if stream != "trade_updates":
                            continue

                        data = message.get("data", {})
                        event_type = data.get("event", "")
                        order_data = data.get("order", {})

                        # Only yield fill-related events
                        if event_type in ("fill", "partial_fill"):
                            fill_event = {
                                "broker_order_id": order_data.get("id", ""),
                                "client_order_id": order_data.get("client_order_id", ""),
                                "symbol": order_data.get("symbol", ""),
                                "side": order_data.get("side", ""),
                                "filled_qty": int(order_data.get("filled_qty", 0) or 0),
                                "filled_price": float(order_data.get("filled_avg_price", 0) or 0),
                                "commission": 0.0,  # Alpaca is commission-free
                                "event_type": event_type,
                                "order_status": order_data.get("status", ""),
                                "timestamp": data.get("timestamp", ""),
                            }

                            logger.info(
                                "alpaca_fill_received",
                                broker_order_id=fill_event["broker_order_id"],
                                symbol=fill_event["symbol"],
                                event_type=event_type,
                                filled_qty=fill_event["filled_qty"],
                            )

                            yield fill_event

                        elif event_type in ("canceled", "rejected", "expired"):
                            # Yield non-fill events for order lifecycle tracking
                            yield {
                                "broker_order_id": order_data.get("id", ""),
                                "client_order_id": order_data.get("client_order_id", ""),
                                "symbol": order_data.get("symbol", ""),
                                "side": order_data.get("side", ""),
                                "filled_qty": int(order_data.get("filled_qty", 0) or 0),
                                "filled_price": float(order_data.get("filled_avg_price", 0) or 0),
                                "commission": 0.0,
                                "event_type": event_type,
                                "order_status": order_data.get("status", ""),
                                "timestamp": data.get("timestamp", ""),
                            }

                except websockets.ConnectionClosed:
                    logger.warning("alpaca_websocket_disconnected_reconnecting")
                    continue

        except Exception as exc:
            raise BrokerConnectionError(
                f"Alpaca WebSocket connection failed: {exc}"
            ) from exc
