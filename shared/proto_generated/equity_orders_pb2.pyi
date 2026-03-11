"""Type stubs for equity_orders_pb2 generated protobuf module."""

from typing import Any

from google.protobuf import timestamp_pb2 as _timestamp_pb2

DESCRIPTOR: Any

class _OrderSide:
    ORDER_SIDE_UNSPECIFIED: int
    ORDER_SIDE_BUY: int
    ORDER_SIDE_SELL: int

class _OrderType:
    ORDER_TYPE_UNSPECIFIED: int
    ORDER_TYPE_MARKET: int
    ORDER_TYPE_LIMIT: int
    ORDER_TYPE_STOP: int
    ORDER_TYPE_STOP_LIMIT: int

class _TimeInForce:
    TIME_IN_FORCE_UNSPECIFIED: int
    TIME_IN_FORCE_DAY: int
    TIME_IN_FORCE_GTC: int
    TIME_IN_FORCE_IOC: int
    TIME_IN_FORCE_FOK: int

class _OrderStatus:
    ORDER_STATUS_UNSPECIFIED: int
    ORDER_STATUS_PENDING_RISK: int
    ORDER_STATUS_RISK_APPROVED: int
    ORDER_STATUS_RISK_REJECTED: int
    ORDER_STATUS_SUBMITTED: int
    ORDER_STATUS_ACKNOWLEDGED: int
    ORDER_STATUS_PARTIAL_FILL: int
    ORDER_STATUS_FILLED: int
    ORDER_STATUS_CANCELLED: int
    ORDER_STATUS_REJECTED: int
    ORDER_STATUS_EXPIRED: int

OrderSide: _OrderSide
OrderType: _OrderType
TimeInForce: _TimeInForce
OrderStatus: _OrderStatus

ORDER_SIDE_UNSPECIFIED: int
ORDER_SIDE_BUY: int
ORDER_SIDE_SELL: int

ORDER_TYPE_UNSPECIFIED: int
ORDER_TYPE_MARKET: int
ORDER_TYPE_LIMIT: int
ORDER_TYPE_STOP: int
ORDER_TYPE_STOP_LIMIT: int

TIME_IN_FORCE_UNSPECIFIED: int
TIME_IN_FORCE_DAY: int
TIME_IN_FORCE_GTC: int
TIME_IN_FORCE_IOC: int
TIME_IN_FORCE_FOK: int

ORDER_STATUS_UNSPECIFIED: int
ORDER_STATUS_PENDING_RISK: int
ORDER_STATUS_RISK_APPROVED: int
ORDER_STATUS_RISK_REJECTED: int
ORDER_STATUS_SUBMITTED: int
ORDER_STATUS_ACKNOWLEDGED: int
ORDER_STATUS_PARTIAL_FILL: int
ORDER_STATUS_FILLED: int
ORDER_STATUS_CANCELLED: int
ORDER_STATUS_REJECTED: int
ORDER_STATUS_EXPIRED: int

class OrderRequest:
    DESCRIPTOR: Any
    client_order_id: str
    strategy_id: str
    symbol: str
    exchange: str
    side: int
    order_type: int
    quantity: int
    limit_price: float
    stop_price: float
    time_in_force: int
    currency: str
    signal_time: _timestamp_pb2.Timestamp
    def __init__(
        self,
        *,
        client_order_id: str = ...,
        strategy_id: str = ...,
        symbol: str = ...,
        exchange: str = ...,
        side: int = ...,
        order_type: int = ...,
        quantity: int = ...,
        limit_price: float = ...,
        stop_price: float = ...,
        time_in_force: int = ...,
        currency: str = ...,
    ) -> None: ...
    def HasField(self, field_name: str) -> bool: ...

class RiskDecision:
    DESCRIPTOR: Any
    client_order_id: str
    status: int
    rejection_reasons: list[str]
    approved_quantity: float
    portfolio_var_before: float
    portfolio_var_after: float
    strategy_id: str
    exchange: str
    decided_at: _timestamp_pb2.Timestamp
    def __init__(
        self,
        *,
        client_order_id: str = ...,
        status: int = ...,
        approved_quantity: float = ...,
        portfolio_var_before: float = ...,
        portfolio_var_after: float = ...,
    ) -> None: ...

class OrderEvent:
    DESCRIPTOR: Any
    event_id: str
    client_order_id: str
    broker_order_id: str
    from_status: int
    to_status: int
    filled_quantity: float
    filled_price: float
    commission: float
    tax: float
    rejection_reason: str
    source: str
    occurred_at: _timestamp_pb2.Timestamp
    def __init__(
        self,
        *,
        event_id: str = ...,
        client_order_id: str = ...,
        broker_order_id: str = ...,
        from_status: int = ...,
        to_status: int = ...,
        filled_quantity: float = ...,
        filled_price: float = ...,
        commission: float = ...,
        tax: float = ...,
        rejection_reason: str = ...,
        source: str = ...,
    ) -> None: ...
