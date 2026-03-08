"""Abstract base class for all Pyhron broker adapters.

Every broker integration (Alpaca, IDX FIX, etc.) must subclass BrokerAdapter
and implement all async methods. The OMS and reconciliation services depend
only on this interface — never on concrete adapters.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import AsyncIterator

from shared.proto_generated.orders_pb2 import OrderRequest


class BrokerAdapter(ABC):
    """Abstract interface for broker connectivity.

    All methods are async to support non-blocking I/O. Concrete adapters
    must implement every method — there are no default implementations.

    Subclasses:
        - AlpacaAdapter: REST + WebSocket for US equities via Alpaca.
        - IDXBrokerAdapter: FIX protocol for Indonesia Stock Exchange (stub).
    """

    @abstractmethod
    async def submit_order(self, order: OrderRequest) -> str:
        """Submit an order to the broker.

        Args:
            order: The OrderRequest protobuf containing all order details
                (symbol, side, quantity, order_type, limit_price, etc.).

        Returns:
            The broker-assigned order ID as a string.

        Raises:
            BrokerConnectionError: If the broker is unreachable.
            OrderRejectedError: If the broker explicitly rejects the order.
            BrokerTimeoutError: If the request times out.
        """
        raise NotImplementedError("submit_order must be implemented by subclass")

    @abstractmethod
    async def cancel_order(self, broker_order_id: str) -> bool:
        """Cancel an existing order at the broker.

        Args:
            broker_order_id: The broker-assigned order ID to cancel.

        Returns:
            True if the cancellation was accepted, False if the order
            could not be cancelled (e.g. already filled).

        Raises:
            BrokerConnectionError: If the broker is unreachable.
            BrokerTimeoutError: If the request times out.
        """
        raise NotImplementedError("cancel_order must be implemented by subclass")

    @abstractmethod
    async def get_order_status(self, broker_order_id: str) -> dict:
        """Retrieve the current status of an order from the broker.

        Args:
            broker_order_id: The broker-assigned order ID.

        Returns:
            A dict with at minimum: ``{"status": str, "filled_qty": int,
            "avg_fill_price": float, "broker_order_id": str}``.

        Raises:
            BrokerConnectionError: If the broker is unreachable.
            BrokerTimeoutError: If the request times out.
        """
        raise NotImplementedError("get_order_status must be implemented by subclass")

    @abstractmethod
    async def get_positions(self) -> list[dict]:
        """Fetch all current positions from the broker.

        Returns:
            A list of dicts, each with at minimum: ``{"symbol": str,
            "qty": int, "market_value": float, "avg_entry_price": float}``.

        Raises:
            BrokerConnectionError: If the broker is unreachable.
        """
        raise NotImplementedError("get_positions must be implemented by subclass")

    @abstractmethod
    async def get_account(self) -> dict:
        """Fetch account information from the broker.

        Returns:
            A dict with at minimum: ``{"equity": float, "cash": float,
            "buying_power": float, "portfolio_value": float}``.

        Raises:
            BrokerConnectionError: If the broker is unreachable.
        """
        raise NotImplementedError("get_account must be implemented by subclass")

    @abstractmethod
    async def stream_fills(self) -> AsyncIterator[dict]:
        """Stream real-time fill events from the broker.

        Yields dicts with at minimum: ``{"broker_order_id": str,
        "client_order_id": str, "filled_qty": int, "filled_price": float,
        "commission": float, "event_type": str}``.

        Yields:
            Fill event dicts as they arrive from the broker.

        Raises:
            BrokerConnectionError: If the WebSocket/stream connection fails.
        """
        raise NotImplementedError("stream_fills must be implemented by subclass")
        # This yield is required to make the method an async generator
        yield  # noqa: unreachable — required for AsyncIterator type hint
