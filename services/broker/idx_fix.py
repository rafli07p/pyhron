"""IDX (Indonesia Stock Exchange) broker adapter stub.

This adapter is a placeholder for the FIX protocol integration with IDX.
The FIX (Financial Information eXchange) protocol is the standard for
electronic trading on the Indonesia Stock Exchange. Full implementation
requires a certified FIX engine (e.g. QuickFIX/J or QuickFIX/n).

All methods raise NotImplementedError with descriptive messages about
what would be needed for a production FIX implementation.
"""

from __future__ import annotations

from typing import AsyncIterator

from services.broker.base import BrokerAdapter
from shared.structured_json_logger import get_logger
from shared.proto_generated.equity_orders_pb2 import OrderRequest

logger = get_logger(__name__)


class IDXBrokerAdapter(BrokerAdapter):
    """Stub adapter for the Indonesia Stock Exchange via FIX protocol.

    The FIX protocol integration requires:
      - A certified FIX engine (QuickFIX/J, QuickFIX/n, or similar).
      - FIX session configuration (SenderCompID, TargetCompID, heartbeat).
      - IDX-specific message fields (lot size 100, T+2 settlement).
      - SSL/TLS certificates from the IDX member broker.
      - Compliance with IDX trading rules (auto-rejection, price limits).

    This stub exists so the codebase can reference IDXBrokerAdapter in
    configuration and dependency injection without breaking at import time.
    All methods raise NotImplementedError until the FIX engine is integrated.
    """

    def __init__(self) -> None:
        logger.warning(
            "idx_broker_adapter_stub_initialized",
            message="IDX FIX protocol adapter is not yet implemented",
        )

    async def submit_order(self, order: OrderRequest) -> str:
        """Submit an order to IDX via FIX protocol.

        Would send a FIX NewSingleOrder (MsgType=D) message with:
          - ClOrdID: order.client_order_id
          - Symbol: order.symbol
          - Side: mapped from proto OrderSide to FIX Side (1=Buy, 2=Sell)
          - OrderQty: order.quantity (must be multiple of lot size 100)
          - OrdType: mapped from proto OrderType to FIX OrdType
          - Price: order.limit_price (for limit orders)
          - TimeInForce: mapped to FIX TIF values

        Args:
            order: The OrderRequest protobuf.

        Raises:
            NotImplementedError: Always — FIX protocol not yet implemented.
        """
        raise NotImplementedError(
            "IDX FIX protocol order submission is not yet implemented. "
            "Requires a certified FIX engine with IDX member broker credentials. "
            f"Would submit order for {order.symbol} qty={order.quantity} "
            "via FIX NewSingleOrder (MsgType=D)."
        )

    async def cancel_order(self, broker_order_id: str) -> bool:
        """Cancel an order on IDX via FIX protocol.

        Would send a FIX OrderCancelRequest (MsgType=F) message with:
          - OrigClOrdID: the original client order ID
          - ClOrdID: a new unique cancel request ID
          - OrderID: broker_order_id from IDX

        Args:
            broker_order_id: The IDX-assigned order ID.

        Raises:
            NotImplementedError: Always — FIX protocol not yet implemented.
        """
        raise NotImplementedError(
            "IDX FIX protocol order cancellation is not yet implemented. "
            "Requires FIX OrderCancelRequest (MsgType=F) with IDX session. "
            f"Would cancel order {broker_order_id}."
        )

    async def get_order_status(self, broker_order_id: str) -> dict:
        """Query order status on IDX via FIX protocol.

        Would send a FIX OrderStatusRequest (MsgType=H) or rely on
        ExecutionReport (MsgType=8) messages received from IDX.

        Args:
            broker_order_id: The IDX-assigned order ID.

        Raises:
            NotImplementedError: Always — FIX protocol not yet implemented.
        """
        raise NotImplementedError(
            "IDX FIX protocol order status query is not yet implemented. "
            "Would use FIX OrderStatusRequest (MsgType=H) or cached "
            f"ExecutionReports for order {broker_order_id}."
        )

    async def get_positions(self) -> list[dict]:
        """Fetch positions from IDX via FIX protocol or broker API.

        IDX positions would typically be retrieved via:
          - FIX PositionReport (MsgType=AP) if supported by the broker.
          - A separate REST API provided by the IDX member broker.
          - The KSEI (Indonesian Central Securities Depository) interface.

        Raises:
            NotImplementedError: Always — FIX protocol not yet implemented.
        """
        raise NotImplementedError(
            "IDX FIX protocol position retrieval is not yet implemented. "
            "Would use FIX PositionReport (MsgType=AP) or broker-specific "
            "REST API for position data from KSEI."
        )

    async def get_account(self) -> dict:
        """Fetch account information from IDX broker.

        IDX account data includes:
          - Trading limit (buying power under T+2 settlement).
          - Cash balance and collateral value.
          - Margin availability for margin accounts.

        Raises:
            NotImplementedError: Always — FIX protocol not yet implemented.
        """
        raise NotImplementedError(
            "IDX FIX protocol account query is not yet implemented. "
            "Would retrieve trading limit, cash balance, and collateral "
            "information from the IDX member broker."
        )

    async def stream_fills(self) -> AsyncIterator[dict]:
        """Stream fill events from IDX via FIX ExecutionReport messages.

        Would listen for FIX ExecutionReport (MsgType=8) messages with:
          - ExecType=F (Trade/Fill)
          - ExecType=1 (Partial Fill)
        And convert them to standardized fill event dicts.

        Raises:
            NotImplementedError: Always — FIX protocol not yet implemented.
        """
        raise NotImplementedError(
            "IDX FIX protocol fill streaming is not yet implemented. "
            "Would process FIX ExecutionReport (MsgType=8) messages with "
            "ExecType=F (Trade) and ExecType=1 (Partial Fill) from the "
            "IDX FIX session."
        )
        # This yield is required to make the method an async generator
        yield  # noqa: unreachable — required for AsyncIterator type hint
