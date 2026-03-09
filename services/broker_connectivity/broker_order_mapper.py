"""Broker order format mapper.

Maps between Pyhron's internal OrderRequest protobuf format and
broker-specific order representations. Centralizes format conversion
logic to keep broker adapters focused on connectivity.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from shared.proto_generated.equity_orders_pb2 import (
    OrderRequest,
    OrderSide,
    OrderType,
    TimeInForce,
)
from shared.proto_generated.equity_positions_pb2 import PositionRecord
from shared.structured_json_logger import get_logger

logger = get_logger(__name__)


# ── Alpaca-specific mappings ─────────────────────────────────────────────────

ALPACA_SIDE_MAP: dict[int, str] = {
    OrderSide.ORDER_SIDE_BUY: "buy",
    OrderSide.ORDER_SIDE_SELL: "sell",
}

ALPACA_ORDER_TYPE_MAP: dict[int, str] = {
    OrderType.ORDER_TYPE_MARKET: "market",
    OrderType.ORDER_TYPE_LIMIT: "limit",
    OrderType.ORDER_TYPE_STOP: "stop",
    OrderType.ORDER_TYPE_STOP_LIMIT: "stop_limit",
}

ALPACA_TIF_MAP: dict[int, str] = {
    TimeInForce.TIME_IN_FORCE_DAY: "day",
    TimeInForce.TIME_IN_FORCE_GTC: "gtc",
    TimeInForce.TIME_IN_FORCE_IOC: "ioc",
    TimeInForce.TIME_IN_FORCE_FOK: "fok",
}

# Reverse mappings for Alpaca -> Pyhron
ALPACA_SIDE_REVERSE: dict[str, int] = {v: k for k, v in ALPACA_SIDE_MAP.items()}
ALPACA_ORDER_TYPE_REVERSE: dict[str, int] = {v: k for k, v in ALPACA_ORDER_TYPE_MAP.items()}
ALPACA_TIF_REVERSE: dict[str, int] = {v: k for k, v in ALPACA_TIF_MAP.items()}


# ── IDX FIX-specific mappings ────────────────────────────────────────────────

IDX_FIX_SIDE_MAP: dict[int, str] = {
    OrderSide.ORDER_SIDE_BUY: "1",  # FIX Side: Buy
    OrderSide.ORDER_SIDE_SELL: "2",  # FIX Side: Sell
}

IDX_FIX_ORDER_TYPE_MAP: dict[int, str] = {
    OrderType.ORDER_TYPE_MARKET: "1",  # FIX OrdType: Market
    OrderType.ORDER_TYPE_LIMIT: "2",  # FIX OrdType: Limit
    OrderType.ORDER_TYPE_STOP: "3",  # FIX OrdType: Stop
    OrderType.ORDER_TYPE_STOP_LIMIT: "4",  # FIX OrdType: Stop Limit
}

IDX_FIX_TIF_MAP: dict[int, str] = {
    TimeInForce.TIME_IN_FORCE_DAY: "0",  # FIX TimeInForce: Day
    TimeInForce.TIME_IN_FORCE_GTC: "1",  # FIX TimeInForce: GTC
    TimeInForce.TIME_IN_FORCE_IOC: "3",  # FIX TimeInForce: IOC
    TimeInForce.TIME_IN_FORCE_FOK: "4",  # FIX TimeInForce: FOK
}

# Reverse mappings for FIX -> Pyhron
IDX_FIX_SIDE_REVERSE: dict[str, int] = {v: k for k, v in IDX_FIX_SIDE_MAP.items()}
IDX_FIX_ORDER_TYPE_REVERSE: dict[str, int] = {v: k for k, v in IDX_FIX_ORDER_TYPE_MAP.items()}
IDX_FIX_TIF_REVERSE: dict[str, int] = {v: k for k, v in IDX_FIX_TIF_MAP.items()}


@dataclass(frozen=True)
class BrokerOrderPayload:
    """A broker-specific order payload ready for submission.

    Attributes:
        broker_name: The target broker identifier (e.g. "ALPACA", "IDX").
        payload: The broker-specific order dict/payload.
        metadata: Additional metadata about the mapping (for auditing).
    """

    broker_name: str
    payload: dict[str, Any]
    metadata: dict[str, Any] = field(default_factory=dict)


class BrokerOrderMapper:
    """Maps between Pyhron OrderRequest protobufs and broker-specific formats.

    Centralizes all order format conversion logic so that broker adapters
    can focus on connectivity and error handling rather than format mapping.

    Supports bidirectional mapping:
      - ``to_broker()``: Convert a Pyhron OrderRequest to a broker-specific payload.
      - ``from_broker()``: Convert a broker response back to Pyhron format.

    Usage::

        mapper = BrokerOrderMapper()

        # Pyhron -> Alpaca
        payload = mapper.to_alpaca_order(order_request)
        print(payload)  # {"symbol": "AAPL", "qty": "100", ...}

        # Alpaca -> Pyhron
        order = mapper.from_alpaca_order(alpaca_response_dict)

        # Unified interface
        broker_payload = mapper.to_broker(order_request, "ALPACA")
        normalized = mapper.from_broker(response_dict, "ALPACA")
    """

    def to_alpaca_order(self, order: OrderRequest) -> dict[str, Any]:
        """Convert a Pyhron OrderRequest to an Alpaca API order payload.

        Args:
            order: The internal OrderRequest protobuf.

        Returns:
            Dict suitable for POST to Alpaca /v2/orders endpoint.
        """
        payload: dict[str, Any] = {
            "symbol": order.symbol,
            "qty": str(int(order.quantity)),
            "side": ALPACA_SIDE_MAP.get(order.side, "buy"),
            "type": ALPACA_ORDER_TYPE_MAP.get(order.order_type, "market"),
            "time_in_force": ALPACA_TIF_MAP.get(order.time_in_force, "day"),
            "client_order_id": order.client_order_id,
        }

        # Add price fields for limit and stop orders
        if order.order_type in (OrderType.ORDER_TYPE_LIMIT, OrderType.ORDER_TYPE_STOP_LIMIT):
            if order.limit_price > 0:
                payload["limit_price"] = str(order.limit_price)

        if order.order_type in (OrderType.ORDER_TYPE_STOP, OrderType.ORDER_TYPE_STOP_LIMIT):
            if order.stop_price > 0:
                payload["stop_price"] = str(order.stop_price)

        return payload

    def from_alpaca_order(self, data: dict[str, Any]) -> OrderRequest:
        """Convert an Alpaca API order response to a Pyhron OrderRequest.

        Args:
            data: Dict from Alpaca GET /v2/orders/{id} response.

        Returns:
            Populated OrderRequest protobuf.
        """
        order = OrderRequest()
        order.client_order_id = data.get("client_order_id", "")
        order.symbol = data.get("symbol", "")

        side_str = data.get("side", "buy")
        order.side = ALPACA_SIDE_REVERSE.get(side_str, OrderSide.ORDER_SIDE_BUY)

        type_str = data.get("type", "market")
        order.order_type = ALPACA_ORDER_TYPE_REVERSE.get(type_str, OrderType.ORDER_TYPE_MARKET)

        qty = data.get("qty")
        if qty is not None:
            order.quantity = int(float(qty))

        limit_price = data.get("limit_price")
        if limit_price is not None:
            order.limit_price = float(limit_price)

        stop_price = data.get("stop_price")
        if stop_price is not None:
            order.stop_price = float(stop_price)

        return order

    def from_alpaca_position(self, data: dict[str, Any]) -> PositionRecord:
        """Convert an Alpaca position response to a PositionRecord protobuf.

        Args:
            data: Dict from Alpaca GET /v2/positions response.

        Returns:
            Populated PositionRecord protobuf.
        """
        position = PositionRecord()
        position.symbol = data.get("symbol", "")
        position.exchange = "ALPACA"
        position.quantity = float(data.get("qty", 0))
        position.average_entry_price = float(data.get("avg_entry_price", 0))
        position.market_value = float(data.get("market_value", 0))
        position.unrealized_pnl = float(data.get("unrealized_pl", 0))
        position.current_price = float(data.get("current_price", 0))

        return position

    def to_fix_new_order(self, order: OrderRequest) -> dict[str, str]:
        """Convert a Pyhron OrderRequest to FIX 4.4 tag-value pairs.

        Produces a dict of FIX tag numbers (as strings) to values,
        suitable for constructing a FIX NewSingleOrder (MsgType=D).

        Args:
            order: The internal OrderRequest protobuf.

        Returns:
            Dict mapping FIX tag numbers (as strings) to values.
        """
        tags: dict[str, str] = {
            "35": "D",  # MsgType: New Order Single
            "11": order.client_order_id,  # ClOrdID
            "55": order.symbol,  # Symbol
            "54": IDX_FIX_SIDE_MAP.get(order.side, "1"),  # Side
            "40": IDX_FIX_ORDER_TYPE_MAP.get(order.order_type, "2"),  # OrdType
            "38": str(int(order.quantity)),  # OrderQty
            "59": IDX_FIX_TIF_MAP.get(order.time_in_force, "0"),  # TimeInForce
            "207": "XIDX",  # SecurityExchange (IDX MIC code)
        }

        if order.limit_price > 0:
            tags["44"] = f"{order.limit_price:.2f}"  # Price

        if order.stop_price > 0:
            tags["99"] = f"{order.stop_price:.2f}"  # StopPx

        return tags

    def from_fix_execution_report(self, tags: dict[str, str]) -> dict[str, Any]:
        """Parse a FIX Execution Report (35=8) into a normalized dict.

        Args:
            tags: Dict of FIX tag-value pairs from the execution report.

        Returns:
            Normalized dict with fields: broker_order_id, client_order_id,
            exec_type, symbol, filled_quantity, filled_price, order_status.
        """
        return {
            "broker_order_id": tags.get("37", ""),  # OrderID
            "client_order_id": tags.get("11", ""),  # ClOrdID
            "exec_type": tags.get("150", ""),  # ExecType
            "symbol": tags.get("55", ""),  # Symbol
            "filled_quantity": int(tags.get("32", "0")),  # LastQty
            "filled_price": float(tags.get("31", "0")),  # LastPx
            "cumulative_quantity": int(tags.get("14", "0")),  # CumQty
            "avg_fill_price": float(tags.get("6", "0")),  # AvgPx
            "order_status": tags.get("39", ""),  # OrdStatus
            "text": tags.get("58", ""),  # Text
            "broker_name": "IDX",
        }

    def to_broker(self, order: OrderRequest, broker_name: str) -> BrokerOrderPayload:
        """Route an OrderRequest to the appropriate broker mapper.

        Args:
            order: The Pyhron OrderRequest protobuf.
            broker_name: Target broker identifier ("ALPACA" or "IDX").

        Returns:
            A BrokerOrderPayload for the specified broker.

        Raises:
            ValueError: If the broker_name is not supported.
        """
        broker_upper = broker_name.upper()
        if broker_upper == "ALPACA":
            return BrokerOrderPayload(
                broker_name="ALPACA",
                payload=self.to_alpaca_order(order),
                metadata={
                    "proto_side": order.side,
                    "proto_order_type": order.order_type,
                    "proto_tif": order.time_in_force,
                },
            )
        if broker_upper == "IDX":
            return BrokerOrderPayload(
                broker_name="IDX",
                payload=self.to_fix_new_order(order),
                metadata={
                    "msg_type": "D",
                    "proto_side": order.side,
                    "proto_order_type": order.order_type,
                    "lot_size_valid": order.quantity % 100 == 0,
                },
            )
        raise ValueError(f"Unsupported broker: {broker_name}. Supported brokers: ALPACA, IDX")

    def from_broker(self, broker_data: dict[str, Any], broker_name: str) -> dict[str, Any]:
        """Route a broker response through the appropriate reverse mapper.

        Args:
            broker_data: The broker-specific response dict.
            broker_name: Source broker identifier ("ALPACA" or "IDX").

        Returns:
            A Pyhron-normalized dict.

        Raises:
            ValueError: If the broker_name is not supported.
        """
        broker_upper = broker_name.upper()
        if broker_upper == "ALPACA":
            order = self.from_alpaca_order(broker_data)
            return {
                "broker_order_id": broker_data.get("id", ""),
                "client_order_id": order.client_order_id,
                "symbol": order.symbol,
                "side": order.side,
                "quantity": order.quantity,
                "order_type": order.order_type,
                "limit_price": order.limit_price,
                "stop_price": order.stop_price,
                "filled_qty": int(broker_data.get("filled_qty", 0) or 0),
                "avg_fill_price": float(broker_data.get("filled_avg_price", 0) or 0),
                "status": broker_data.get("status", "unknown"),
                "broker_name": "ALPACA",
            }
        if broker_upper == "IDX":
            return self.from_fix_execution_report(broker_data)
        raise ValueError(f"Unsupported broker: {broker_name}. Supported brokers: ALPACA, IDX")
