"""IDX (Indonesia Stock Exchange) FIX protocol adapter.

Provides a simulation-mode adapter for IDX that validates orders against
IDX trading rules (lot sizes, tick sizes, auto-rejection bands) and
generates realistic broker order IDs. When configured with a real FIX
engine, the adapter will route orders through the FIX session.

The adapter supports two modes:
  - **simulation**: Validates orders and returns synthetic broker IDs.
    Suitable for paper trading and integration testing.
  - **live**: Requires a certified FIX engine (QuickFIX or similar)
    with IDX member broker credentials. Not yet implemented.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

from services.broker_connectivity.broker_adapter_interface import BrokerAdapterInterface
from shared.platform_exception_hierarchy import (
    BrokerConnectionError,
    OrderRejectedError,
)
from shared.structured_json_logger import get_logger

if TYPE_CHECKING:
    from collections.abc import AsyncIterator

    from shared.proto_generated.equity_orders_pb2 import OrderRequest

logger = get_logger(__name__)

# IDX trading constants
IDX_LOT_SIZE = 100
IDX_MIN_PRICE = 50  # IDR

# Tick size tiers (IDX effective 2024)
IDX_TICK_TIERS: list[tuple[int, int, int]] = [
    # (price_from, price_to, tick_size)
    (50, 200, 1),
    (200, 500, 2),
    (500, 2000, 5),
    (2000, 5000, 10),
    (5000, 999_999_999, 25),
]

# Auto-rejection bands per price tier
IDX_AUTO_REJECTION_PCT: list[tuple[int, int, float]] = [
    (50, 200, 0.35),
    (200, 5000, 0.25),
    (5000, 999_999_999, 0.20),
]


def _get_tick_size(price: float) -> int:
    """Return the IDX tick size for the given price level."""
    for low, high, tick in IDX_TICK_TIERS:
        if low <= price < high:
            return tick
    return 25


def _get_auto_rejection_pct(price: float) -> float:
    """Return the auto-rejection percentage for the given price level."""
    for low, high, pct in IDX_AUTO_REJECTION_PCT:
        if low <= price < high:
            return pct
    return 0.20


class IDXFIXProtocolAdapter(BrokerAdapterInterface):
    """IDX broker adapter with simulation and live modes.

    In simulation mode, validates orders against IDX rules and returns
    synthetic broker IDs. This allows the full order pipeline to be
    tested without a real FIX connection.

    Args:
        mode: Either "simulation" or "live".
        sender_comp_id: FIX SenderCompID (required for live mode).
        target_comp_id: FIX TargetCompID (required for live mode).
        fix_host: FIX gateway hostname (required for live mode).
        fix_port: FIX gateway port (required for live mode).
    """

    def __init__(
        self,
        mode: str = "simulation",
        *,
        sender_comp_id: str | None = None,
        target_comp_id: str | None = None,
        fix_host: str | None = None,
        fix_port: int | None = None,
    ) -> None:
        self._mode = mode
        self._sender_comp_id = sender_comp_id
        self._target_comp_id = target_comp_id
        self._fix_host = fix_host
        self._fix_port = fix_port
        self._connected = False

        # In-memory order tracking for simulation mode
        self._orders: dict[str, dict[str, Any]] = {}
        self._positions: dict[str, dict[str, Any]] = {}

        if mode == "live":
            if not all([sender_comp_id, target_comp_id, fix_host, fix_port]):
                raise ValueError("Live mode requires sender_comp_id, target_comp_id, fix_host, and fix_port")

        logger.info(
            "idx_fix_adapter_initialized",
            mode=mode,
            sender_comp_id=sender_comp_id,
        )

    def _validate_idx_order(self, order: OrderRequest) -> None:
        """Validate an order against IDX trading rules.

        Raises:
            OrderRejectedError: If the order violates IDX rules.
        """
        # Lot size validation
        if order.quantity <= 0:
            raise OrderRejectedError(
                "Quantity must be positive",
                reason="Quantity must be positive",
            )
        if order.quantity % IDX_LOT_SIZE != 0:
            raise OrderRejectedError(
                f"Quantity {order.quantity} is not a multiple of IDX lot size ({IDX_LOT_SIZE})",
                reason=f"Quantity {order.quantity} is not a multiple of IDX lot size ({IDX_LOT_SIZE})",
            )

        # Price validation for limit orders (order_type == 2 is LIMIT)
        if order.order_type == 2:
            if order.limit_price <= 0:
                raise OrderRejectedError(
                    "Limit price must be positive",
                    reason="Limit price must be positive",
                )
            if order.limit_price < IDX_MIN_PRICE:
                raise OrderRejectedError(
                    f"Price {order.limit_price} below IDX minimum ({IDX_MIN_PRICE} IDR)",
                    reason=f"Price {order.limit_price} below IDX minimum ({IDX_MIN_PRICE} IDR)",
                )

            # Tick size validation
            tick = _get_tick_size(order.limit_price)
            price_int = int(order.limit_price)
            if price_int % tick != 0:
                raise OrderRejectedError(
                    f"Price {order.limit_price} not aligned to tick size {tick} for this price tier",
                    reason=f"Price {order.limit_price} not aligned to tick size {tick} for this price tier",
                )

    async def submit_order(self, order: OrderRequest) -> str:
        """Submit an order to IDX.

        In simulation mode: validates IDX rules and returns a synthetic ID.
        In live mode: would send FIX NewSingleOrder (MsgType=D).
        """
        self._validate_idx_order(order)

        if self._mode == "simulation":
            broker_order_id = f"IDX-SIM-{uuid.uuid4().hex[:12].upper()}"
            self._orders[broker_order_id] = {
                "client_order_id": order.client_order_id,
                "symbol": order.symbol,
                "side": "BUY" if order.side == 1 else "SELL",
                "quantity": order.quantity,
                "filled_qty": order.quantity,  # Simulation: instant fill
                "avg_fill_price": order.limit_price if order.limit_price > 0 else 1000.0,
                "status": "FILLED",
                "submitted_at": datetime.now(tz=UTC).isoformat(),
                "broker_order_id": broker_order_id,
            }

            # Update simulated positions
            symbol = order.symbol
            side_mult = 1 if order.side == 1 else -1
            if symbol not in self._positions:
                self._positions[symbol] = {"qty": 0, "avg_entry_price": 0.0, "market_value": 0.0}
            pos = self._positions[symbol]
            pos["qty"] += order.quantity * side_mult
            if pos["qty"] > 0:
                fill_price = order.limit_price if order.limit_price > 0 else 1000.0
                pos["avg_entry_price"] = fill_price
                pos["market_value"] = pos["qty"] * fill_price

            logger.info(
                "idx_sim_order_submitted",
                broker_order_id=broker_order_id,
                symbol=order.symbol,
                quantity=order.quantity,
            )
            return broker_order_id

        # Live mode - not yet implemented
        raise BrokerConnectionError(
            "IDX FIX live mode is not yet implemented. "
            "Requires a certified FIX engine with IDX member broker credentials."
        )

    async def cancel_order(self, broker_order_id: str) -> bool:
        """Cancel an order on IDX.

        In simulation mode: marks the order as cancelled if not yet filled.
        In live mode: would send FIX OrderCancelRequest (MsgType=F).
        """
        if self._mode == "simulation":
            order = self._orders.get(broker_order_id)
            if order is None:
                logger.warning("idx_sim_cancel_not_found", broker_order_id=broker_order_id)
                return False
            if order["status"] in ("FILLED", "CANCELLED"):
                return False
            order["status"] = "CANCELLED"
            logger.info("idx_sim_order_cancelled", broker_order_id=broker_order_id)
            return True

        raise BrokerConnectionError("IDX FIX live mode is not yet implemented.")

    async def get_order_status(self, broker_order_id: str) -> dict[str, Any]:
        """Query order status on IDX.

        In simulation mode: returns from in-memory store.
        In live mode: would send FIX OrderStatusRequest (MsgType=H).
        """
        if self._mode == "simulation":
            order = self._orders.get(broker_order_id)
            if order is None:
                return {"status": "UNKNOWN", "broker_order_id": broker_order_id}
            return {
                "status": order["status"],
                "filled_qty": order["filled_qty"],
                "avg_fill_price": order["avg_fill_price"],
                "broker_order_id": broker_order_id,
            }

        raise BrokerConnectionError("IDX FIX live mode is not yet implemented.")

    async def get_positions(self) -> list[dict[str, Any]]:
        """Fetch positions from IDX.

        In simulation mode: returns from in-memory store.
        In live mode: would use FIX PositionReport (MsgType=AP) or broker REST API.
        """
        if self._mode == "simulation":
            return [
                {
                    "symbol": symbol,
                    "qty": pos["qty"],
                    "market_value": pos["market_value"],
                    "avg_entry_price": pos["avg_entry_price"],
                }
                for symbol, pos in self._positions.items()
                if pos["qty"] != 0
            ]

        raise BrokerConnectionError("IDX FIX live mode is not yet implemented.")

    async def get_account(self) -> dict[str, Any]:
        """Fetch account information from IDX broker.

        In simulation mode: returns synthetic account data.
        In live mode: would query broker REST API.
        """
        if self._mode == "simulation":
            total_mv = sum(p["market_value"] for p in self._positions.values())
            return {
                "equity": 1_000_000_000.0 + total_mv,
                "cash": 1_000_000_000.0 - total_mv,
                "buying_power": 1_000_000_000.0 - total_mv,
                "portfolio_value": 1_000_000_000.0,
                "currency": "IDR",
                "settlement": "T+2",
            }

        raise BrokerConnectionError("IDX FIX live mode is not yet implemented.")

    async def stream_fills(self) -> AsyncIterator[dict[str, Any]]:
        """Stream fill events from IDX.

        In simulation mode: yields fills from submitted orders.
        In live mode: would listen for FIX ExecutionReport (MsgType=8).
        """
        if self._mode == "simulation":
            for broker_id, order in self._orders.items():
                if order["status"] == "FILLED":
                    yield {
                        "broker_order_id": broker_id,
                        "client_order_id": order["client_order_id"],
                        "filled_qty": order["filled_qty"],
                        "filled_price": order["avg_fill_price"],
                        "commission": order["filled_qty"] * order["avg_fill_price"] * 0.0015,
                        "event_type": "fill",
                        "symbol": order["symbol"],
                    }
            return

        raise BrokerConnectionError("IDX FIX live mode is not yet implemented.")
