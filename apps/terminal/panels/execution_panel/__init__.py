"""Execution Panel for the Enthropy Terminal.

Provides order entry, management, and fill monitoring capabilities.
Integrates with the DataClient to submit orders and track execution
status through the OMS.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any
from uuid import UUID, uuid4

from shared.schemas.order_events import (
    OrderRequest,
    OrderSide,
    OrderType,
    TimeInForce,
)

logger = logging.getLogger(__name__)


@dataclass
class OrderEntry:
    """Local representation of an order for display purposes."""

    order_id: UUID = field(default_factory=uuid4)
    symbol: str = ""
    side: str = "BUY"
    order_type: str = "LIMIT"
    qty: Decimal = Decimal("0")
    price: Decimal | None = None
    status: str = "PENDING"
    filled_qty: Decimal = Decimal("0")
    avg_fill_price: Decimal | None = None
    submitted_at: datetime | None = None
    last_updated: datetime | None = None


class ExecutionPanel:
    """Order entry and execution management panel.

    Provides a UI-oriented interface for submitting new orders, viewing
    open orders and fills, and cancelling orders. All operations route
    through the terminal's DataClient to the execution service.

    Parameters
    ----------
    data_client:
        Instance of ``apps.terminal.data_client.DataClient`` for order
        submission and status queries. If ``None``, operates in offline mode.
    tenant_id:
        Tenant identifier for multi-tenancy.
    """

    def __init__(self, data_client: Any = None, tenant_id: str = "default") -> None:
        self._data_client = data_client
        self._tenant_id = tenant_id
        self._open_orders: dict[str, OrderEntry] = {}
        self._fills: list[dict[str, Any]] = []
        logger.info("ExecutionPanel initialized (tenant_id=%s)", tenant_id)

    @property
    def open_order_count(self) -> int:
        """Number of currently open orders."""
        return len(self._open_orders)

    async def submit_order(
        self,
        symbol: str,
        side: str,
        qty: Decimal,
        order_type: str = "LIMIT",
        price: Decimal | None = None,
        time_in_force: str = "DAY",
        stop_price: Decimal | None = None,
        account_id: str | None = None,
    ) -> dict[str, Any]:
        """Submit a new order through the execution service.

        Parameters
        ----------
        symbol:
            Instrument symbol (e.g., ``AAPL``).
        side:
            ``BUY`` or ``SELL``.
        qty:
            Order quantity.
        order_type:
            One of ``MARKET``, ``LIMIT``, ``STOP``, ``STOP_LIMIT``.
        price:
            Limit price (required for LIMIT and STOP_LIMIT orders).
        time_in_force:
            Time-in-force instruction (``DAY``, ``GTC``, ``IOC``, ``FOK``).
        stop_price:
            Stop trigger price for STOP / STOP_LIMIT orders.
        account_id:
            Optional trading account identifier.

        Returns
        -------
        dict[str, Any]
            Order submission result with order ID and initial status.
        """
        order_request = OrderRequest(
            symbol=symbol,
            side=OrderSide(side),
            qty=qty,
            order_type=OrderType(order_type),
            price=price,
            time_in_force=TimeInForce(time_in_force),
            stop_price=stop_price,
            account_id=account_id,
            tenant_id=self._tenant_id,
        )

        entry = OrderEntry(
            order_id=order_request.order_id,
            symbol=symbol,
            side=side,
            order_type=order_type,
            qty=qty,
            price=price,
            status="SUBMITTED",
            submitted_at=datetime.now(tz=UTC),
        )

        result: dict[str, Any] = {"order_id": str(entry.order_id), "status": "SUBMITTED"}

        if self._data_client is not None:
            try:
                response = await self._data_client.submit_order(order_request.model_dump(mode="json"))
                if isinstance(response, dict):
                    entry.status = response.get("status", "SUBMITTED")
                    result.update(response)
            except Exception as exc:
                logger.error("Order submission failed for %s: %s", symbol, exc)
                entry.status = "REJECTED"
                result["status"] = "REJECTED"
                result["error"] = str(exc)

        self._open_orders[str(entry.order_id)] = entry
        logger.info("Submitted %s %s %s %s @ %s", side, qty, symbol, order_type, price)
        return result

    def show_open_orders(self) -> list[dict[str, Any]]:
        """Return all currently open orders.

        Returns
        -------
        list[dict[str, Any]]
            List of open order details.
        """
        active_statuses = {"PENDING", "SUBMITTED", "ACKNOWLEDGED", "PARTIALLY_FILLED"}
        return [
            {
                "order_id": str(o.order_id),
                "symbol": o.symbol,
                "side": o.side,
                "order_type": o.order_type,
                "qty": str(o.qty),
                "price": str(o.price) if o.price else None,
                "status": o.status,
                "filled_qty": str(o.filled_qty),
                "submitted_at": o.submitted_at.isoformat() if o.submitted_at else None,
            }
            for o in self._open_orders.values()
            if o.status in active_statuses
        ]

    def show_fills(self) -> list[dict[str, Any]]:
        """Return all recent fill events.

        Returns
        -------
        list[dict[str, Any]]
            List of fill details.
        """
        return list(self._fills)

    async def cancel_order(self, order_id: str) -> dict[str, Any]:
        """Cancel an open order.

        Parameters
        ----------
        order_id:
            UUID string of the order to cancel.

        Returns
        -------
        dict[str, Any]
            Cancellation result.

        Raises
        ------
        KeyError
            If the order ID is not found.
        """
        if order_id not in self._open_orders:
            raise KeyError(f"Order not found: {order_id}")

        entry = self._open_orders[order_id]
        result: dict[str, Any] = {"order_id": order_id, "status": "CANCEL_REQUESTED"}

        if self._data_client is not None:
            try:
                response = await self._data_client.submit_order(
                    {"action": "cancel", "order_id": order_id, "tenant_id": self._tenant_id}
                )
                if isinstance(response, dict):
                    result.update(response)
            except Exception as exc:
                logger.error("Cancel failed for order %s: %s", order_id, exc)
                result["error"] = str(exc)

        entry.status = "CANCELLED"
        entry.last_updated = datetime.now(tz=UTC)
        logger.info("Cancelled order %s (%s %s)", order_id, entry.symbol, entry.side)
        return result

    def _on_fill(self, fill_data: dict[str, Any]) -> None:
        """Handle an incoming fill event from the execution service."""
        order_id = fill_data.get("order_id", "")
        self._fills.append(fill_data)

        if order_id in self._open_orders:
            entry = self._open_orders[order_id]
            entry.filled_qty = Decimal(str(fill_data.get("cumulative_qty", entry.filled_qty)))
            entry.avg_fill_price = Decimal(str(fill_data["fill_price"])) if "fill_price" in fill_data else None
            entry.status = fill_data.get("status", entry.status)
            entry.last_updated = datetime.now(tz=UTC)


__all__ = [
    "ExecutionPanel",
    "OrderEntry",
]
