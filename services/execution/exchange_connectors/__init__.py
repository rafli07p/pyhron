"""Exchange connectors for the Pyhron execution service.

Provides a base connector ABC and concrete implementations for:
- **Alpaca** (equities) via the ``alpaca-py`` library
- **CCXT** (crypto) via the ``ccxt`` library

All connectors are async-first, thread-safe, and include retry logic
powered by :pypi:`tenacity`.  API credentials are read exclusively from
environment variables -- never hard-coded.
"""

from __future__ import annotations

import asyncio
import os
from abc import ABC, abstractmethod
from datetime import UTC, datetime, timezone
from decimal import Decimal
from typing import Any, Optional
from uuid import uuid4

import structlog
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from shared.schemas.order_events import (
    OrderFill,
    OrderRequest,
    OrderSide,
    OrderStatusEnum,
    OrderType,
)

logger = structlog.get_logger(__name__)


# Base connector


class BaseConnector(ABC):
    """Abstract base class for all exchange connectors.

    Every concrete connector must implement the five core operations
    (connect, disconnect, submit, cancel, positions) plus account info
    retrieval.
    """

    def __init__(self, name: str) -> None:
        self.name = name
        self._connected = False
        self._lock = asyncio.Lock()

    @property
    def connected(self) -> bool:
        return self._connected

    @abstractmethod
    async def connect(self) -> None:
        """Establish connection / authenticate with the exchange."""

    @abstractmethod
    async def disconnect(self) -> None:
        """Gracefully close the connection."""

    @abstractmethod
    async def submit_order(self, order: OrderRequest) -> OrderFill:
        """Submit an order and return the resulting fill (or partial fill)."""

    @abstractmethod
    async def cancel_order(self, order_id: str) -> dict[str, Any]:
        """Cancel an open order by its exchange-side identifier."""

    @abstractmethod
    async def get_order_status(self, order_id: str) -> dict[str, Any]:
        """Query the current status of an order."""

    @abstractmethod
    async def get_positions(self) -> list[dict[str, Any]]:
        """Return a list of current positions."""

    @abstractmethod
    async def get_account(self) -> dict[str, Any]:
        """Return account / balance information."""


# Alpaca connector (equities) -- real alpaca-py API


class AlpacaConnector(BaseConnector):
    """Connector for *Alpaca Markets* using the official ``alpaca-py`` SDK.

    Environment variables:
        ``ALPACA_API_KEY``      -- API key id
        ``ALPACA_SECRET_KEY``   -- API secret key
        ``ALPACA_PAPER``        -- set to ``"true"`` (default) for paper trading
    """

    def __init__(self) -> None:
        super().__init__(name="alpaca")
        self._client: Any = None

    # lifecycle

    async def connect(self) -> None:
        async with self._lock:
            if self._connected:
                return

            from alpaca.trading.client import TradingClient

            api_key = os.environ["ALPACA_API_KEY"]
            secret_key = os.environ["ALPACA_SECRET_KEY"]
            paper = os.environ.get("ALPACA_PAPER", "true").lower() == "true"

            self._client = TradingClient(
                api_key=api_key,
                secret_key=secret_key,
                paper=paper,
            )
            self._connected = True
            logger.info("alpaca.connected", paper=paper)

    async def disconnect(self) -> None:
        async with self._lock:
            self._client = None
            self._connected = False
            logger.info("alpaca.disconnected")

    # orders

    @retry(
        retry=retry_if_exception_type((ConnectionError, TimeoutError)),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=0.5, max=4),
        reraise=True,
    )
    async def submit_order(self, order: OrderRequest) -> OrderFill:
        """Submit an order to Alpaca and return an :class:`OrderFill`."""
        async with self._lock:
            if not self._connected or self._client is None:
                raise ConnectionError("AlpacaConnector is not connected")

            from alpaca.trading.enums import OrderSide as AlpacaSide
            from alpaca.trading.enums import TimeInForce as AlpacaTIF
            from alpaca.trading.requests import (
                LimitOrderRequest,
                MarketOrderRequest,
                StopLimitOrderRequest,
                StopOrderRequest,
            )

            tif_map = {
                "DAY": AlpacaTIF.DAY,
                "GTC": AlpacaTIF.GTC,
                "IOC": AlpacaTIF.IOC,
                "FOK": AlpacaTIF.FOK,
                "OPG": AlpacaTIF.OPG,
            }
            alpaca_side = AlpacaSide.BUY if order.side == OrderSide.BUY else AlpacaSide.SELL
            alpaca_tif = tif_map.get(order.time_in_force.value, AlpacaTIF.DAY)

            req: MarketOrderRequest | LimitOrderRequest | StopOrderRequest | StopLimitOrderRequest
            if order.order_type == OrderType.MARKET:
                req = MarketOrderRequest(
                    symbol=order.symbol,
                    qty=float(order.qty),
                    side=alpaca_side,
                    time_in_force=alpaca_tif,
                )
            elif order.order_type == OrderType.LIMIT:
                req = LimitOrderRequest(
                    symbol=order.symbol,
                    qty=float(order.qty),
                    side=alpaca_side,
                    time_in_force=alpaca_tif,
                    limit_price=float(order.price or Decimal("0")),
                )
            elif order.order_type == OrderType.STOP:
                req = StopOrderRequest(
                    symbol=order.symbol,
                    qty=float(order.qty),
                    side=alpaca_side,
                    time_in_force=alpaca_tif,
                    stop_price=float(order.stop_price or Decimal("0")),
                )
            elif order.order_type == OrderType.STOP_LIMIT:
                req = StopLimitOrderRequest(
                    symbol=order.symbol,
                    qty=float(order.qty),
                    side=alpaca_side,
                    time_in_force=alpaca_tif,
                    limit_price=float(order.price or Decimal("0")),
                    stop_price=float(order.stop_price or Decimal("0")),
                )
            else:
                raise ValueError(f"Unsupported Alpaca order type: {order.order_type}")

            # Alpaca SDK call -- synchronous, run in executor to avoid blocking
            loop = asyncio.get_running_loop()
            response = await loop.run_in_executor(None, self._client.submit_order, req)

            fill_price = Decimal(str(response.filled_avg_price)) if response.filled_avg_price else order.price or Decimal("0")
            filled_qty = Decimal(str(response.filled_qty)) if response.filled_qty else order.qty
            leaves = order.qty - filled_qty

            status = OrderStatusEnum.FILLED if leaves == 0 else OrderStatusEnum.PARTIALLY_FILLED
            if str(response.status).upper() == "ACCEPTED":
                status = OrderStatusEnum.SUBMITTED

            logger.info(
                "alpaca.order_submitted",
                order_id=str(order.order_id),
                alpaca_id=str(response.id),
                status=status.value,
            )

            return OrderFill(
                fill_id=uuid4(),
                order_id=order.order_id,
                symbol=order.symbol,
                side=order.side,
                qty=order.qty,
                price=fill_price,
                order_type=order.order_type,
                tenant_id=order.tenant_id,
                fill_qty=filled_qty,
                fill_price=fill_price,
                cumulative_qty=filled_qty,
                leaves_qty=leaves,
                status=status,
                exchange="ALPACA",
                timestamp=datetime.now(UTC),
            )

    @retry(
        retry=retry_if_exception_type((ConnectionError, TimeoutError)),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=0.5, max=4),
        reraise=True,
    )
    async def cancel_order(self, order_id: str) -> dict[str, Any]:
        async with self._lock:
            if not self._connected or self._client is None:
                raise ConnectionError("AlpacaConnector is not connected")
            loop = asyncio.get_running_loop()
            await loop.run_in_executor(None, self._client.cancel_order_by_id, order_id)
            logger.info("alpaca.order_cancelled", order_id=order_id)
            return {"order_id": order_id, "status": "cancelled"}

    async def get_order_status(self, order_id: str) -> dict[str, Any]:
        async with self._lock:
            if not self._connected or self._client is None:
                raise ConnectionError("AlpacaConnector is not connected")
            loop = asyncio.get_running_loop()
            resp = await loop.run_in_executor(None, self._client.get_order_by_id, order_id)
            return {
                "order_id": str(resp.id),
                "status": str(resp.status),
                "filled_qty": str(resp.filled_qty),
                "filled_avg_price": str(resp.filled_avg_price),
                "symbol": resp.symbol,
            }

    async def get_positions(self) -> list[dict[str, Any]]:
        async with self._lock:
            if not self._connected or self._client is None:
                raise ConnectionError("AlpacaConnector is not connected")
            loop = asyncio.get_running_loop()
            positions = await loop.run_in_executor(None, self._client.get_all_positions)
            return [
                {
                    "symbol": p.symbol,
                    "qty": str(p.qty),
                    "side": str(p.side),
                    "market_value": str(p.market_value),
                    "avg_entry_price": str(p.avg_entry_price),
                    "unrealized_pl": str(p.unrealized_pl),
                    "current_price": str(p.current_price),
                }
                for p in positions
            ]

    async def get_account(self) -> dict[str, Any]:
        async with self._lock:
            if not self._connected or self._client is None:
                raise ConnectionError("AlpacaConnector is not connected")
            loop = asyncio.get_running_loop()
            acct = await loop.run_in_executor(None, self._client.get_account)
            return {
                "id": str(acct.id),
                "buying_power": str(acct.buying_power),
                "cash": str(acct.cash),
                "equity": str(acct.equity),
                "portfolio_value": str(acct.portfolio_value),
                "status": str(acct.status),
            }


# CCXT connector (crypto) -- real ccxt API


class CCXTConnector(BaseConnector):
    """Connector for crypto exchanges via the ``ccxt`` library.

    Environment variables:
        ``CCXT_EXCHANGE``       -- exchange id (e.g. ``"binance"``, ``"coinbasepro"``)
        ``CCXT_API_KEY``        -- exchange API key
        ``CCXT_SECRET``         -- exchange API secret
        ``CCXT_PASSWORD``       -- passphrase (required by some exchanges)
        ``CCXT_SANDBOX``        -- ``"true"`` to enable sandbox / testnet mode
    """

    def __init__(self, exchange_id: str | None = None) -> None:
        super().__init__(name="ccxt")
        self._exchange_id: str = exchange_id if exchange_id is not None else os.environ.get("CCXT_EXCHANGE", "binance")
        self._exchange: Any = None

    async def connect(self) -> None:
        async with self._lock:
            if self._connected:
                return

            import ccxt

            exchange_class = getattr(ccxt, self._exchange_id, None)
            if exchange_class is None:
                raise ValueError(f"Unsupported CCXT exchange: {self._exchange_id}")

            config: dict[str, Any] = {
                "apiKey": os.environ.get("CCXT_API_KEY", ""),
                "secret": os.environ.get("CCXT_SECRET", ""),
                "enableRateLimit": True,
            }
            password = os.environ.get("CCXT_PASSWORD")
            if password:
                config["password"] = password

            self._exchange = exchange_class(config)

            if os.environ.get("CCXT_SANDBOX", "false").lower() == "true":
                self._exchange.set_sandbox_mode(True)

            # Load markets synchronously in executor
            loop = asyncio.get_running_loop()
            await loop.run_in_executor(None, self._exchange.load_markets)

            self._connected = True
            logger.info(
                "ccxt.connected",
                exchange=self._exchange_id,
                sandbox=os.environ.get("CCXT_SANDBOX", "false"),
            )

    async def disconnect(self) -> None:
        async with self._lock:
            self._exchange = None
            self._connected = False
            logger.info("ccxt.disconnected", exchange=self._exchange_id)

    @retry(
        retry=retry_if_exception_type((ConnectionError, TimeoutError)),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=0.5, max=4),
        reraise=True,
    )
    async def submit_order(self, order: OrderRequest) -> OrderFill:
        """Place an order via ``exchange.create_order()``."""
        async with self._lock:
            if not self._connected or self._exchange is None:
                raise ConnectionError("CCXTConnector is not connected")

            side_str = "buy" if order.side == OrderSide.BUY else "sell"
            order_type_str = "market" if order.order_type == OrderType.MARKET else "limit"
            price = float(order.price) if order.price else None

            loop = asyncio.get_running_loop()
            response = await loop.run_in_executor(
                None,
                self._exchange.create_order,
                order.symbol,           # symbol (e.g. "BTC/USDT")
                order_type_str,         # type
                side_str,               # side
                float(order.qty),       # amount
                price,                  # price (None for market)
            )

            filled_qty = Decimal(str(response.get("filled", 0) or 0))
            avg_price = Decimal(str(response.get("average", 0) or response.get("price", 0) or 0))
            remaining = Decimal(str(response.get("remaining", 0) or 0))
            total_qty = filled_qty + remaining if remaining else order.qty

            status = OrderStatusEnum.FILLED if remaining == 0 and filled_qty > 0 else OrderStatusEnum.SUBMITTED
            if filled_qty > 0 and remaining > 0:
                status = OrderStatusEnum.PARTIALLY_FILLED

            fee = Decimal(str(response.get("fee", {}).get("cost", 0) or 0))

            logger.info(
                "ccxt.order_submitted",
                order_id=str(order.order_id),
                exchange_order_id=response.get("id"),
                exchange=self._exchange_id,
                status=status.value,
            )

            return OrderFill(
                fill_id=uuid4(),
                order_id=order.order_id,
                symbol=order.symbol,
                side=order.side,
                qty=total_qty,
                price=avg_price if avg_price > 0 else order.price or Decimal("0"),
                order_type=order.order_type,
                tenant_id=order.tenant_id,
                fill_qty=filled_qty if filled_qty > 0 else order.qty,
                fill_price=avg_price if avg_price > 0 else order.price or Decimal("0"),
                cumulative_qty=filled_qty if filled_qty > 0 else order.qty,
                leaves_qty=remaining,
                status=status,
                exchange=self._exchange_id.upper(),
                commission=fee,
                timestamp=datetime.now(UTC),
            )

    @retry(
        retry=retry_if_exception_type((ConnectionError, TimeoutError)),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=0.5, max=4),
        reraise=True,
    )
    async def cancel_order(self, order_id: str) -> dict[str, Any]:
        async with self._lock:
            if not self._connected or self._exchange is None:
                raise ConnectionError("CCXTConnector is not connected")
            loop = asyncio.get_running_loop()
            result = await loop.run_in_executor(None, self._exchange.cancel_order, order_id)
            logger.info("ccxt.order_cancelled", order_id=order_id, exchange=self._exchange_id)
            return {"order_id": order_id, "status": "cancelled", "raw": result}

    async def get_order_status(self, order_id: str) -> dict[str, Any]:
        async with self._lock:
            if not self._connected or self._exchange is None:
                raise ConnectionError("CCXTConnector is not connected")
            loop = asyncio.get_running_loop()
            resp = await loop.run_in_executor(None, self._exchange.fetch_order, order_id)
            return {
                "order_id": resp.get("id"),
                "status": resp.get("status"),
                "filled": str(resp.get("filled")),
                "remaining": str(resp.get("remaining")),
                "average": str(resp.get("average")),
                "symbol": resp.get("symbol"),
            }

    async def get_positions(self) -> list[dict[str, Any]]:
        async with self._lock:
            if not self._connected or self._exchange is None:
                raise ConnectionError("CCXTConnector is not connected")
            loop = asyncio.get_running_loop()
            balance = await loop.run_in_executor(None, self._exchange.fetch_balance)
            positions: list[dict[str, Any]] = []
            for currency, info in balance.get("total", {}).items():
                if info and float(info) > 0:
                    positions.append({
                        "symbol": currency,
                        "qty": str(info),
                        "free": str(balance.get("free", {}).get(currency, 0)),
                        "used": str(balance.get("used", {}).get(currency, 0)),
                    })
            return positions

    async def get_account(self) -> dict[str, Any]:
        async with self._lock:
            if not self._connected or self._exchange is None:
                raise ConnectionError("CCXTConnector is not connected")
            loop = asyncio.get_running_loop()
            balance = await loop.run_in_executor(None, self._exchange.fetch_balance)
            return {
                "exchange": self._exchange_id,
                "total": {k: str(v) for k, v in balance.get("total", {}).items() if v},
                "free": {k: str(v) for k, v in balance.get("free", {}).items() if v},
                "used": {k: str(v) for k, v in balance.get("used", {}).items() if v},
            }


__all__ = [
    "AlpacaConnector",
    "BaseConnector",
    "CCXTConnector",
]
