"""Auto-generated Protobuf bindings for equity_orders.proto.

Regenerate with: bash scripts/generate_protobuf_python_bindings.sh

These are stub definitions that mirror the .proto file structure.
In production, this file is replaced by protoc-generated code.
"""

from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from google.protobuf import symbol_database as _symbol_database

_sym_db = _symbol_database.Default()

# Enum value constants for OrderSide
ORDER_SIDE_UNSPECIFIED = 0
ORDER_SIDE_BUY = 1
ORDER_SIDE_SELL = 2

# Enum value constants for OrderType
ORDER_TYPE_UNSPECIFIED = 0
ORDER_TYPE_MARKET = 1
ORDER_TYPE_LIMIT = 2
ORDER_TYPE_STOP = 3
ORDER_TYPE_STOP_LIMIT = 4

# Enum value constants for TimeInForce
TIME_IN_FORCE_UNSPECIFIED = 0
TIME_IN_FORCE_DAY = 1
TIME_IN_FORCE_GTC = 2
TIME_IN_FORCE_IOC = 3
TIME_IN_FORCE_FOK = 4

# Enum value constants for OrderStatus
ORDER_STATUS_UNSPECIFIED = 0
ORDER_STATUS_PENDING_RISK = 1
ORDER_STATUS_RISK_APPROVED = 2
ORDER_STATUS_RISK_REJECTED = 3
ORDER_STATUS_SUBMITTED = 4
ORDER_STATUS_ACKNOWLEDGED = 5
ORDER_STATUS_PARTIAL_FILL = 6
ORDER_STATUS_FILLED = 7
ORDER_STATUS_CANCELLED = 8
ORDER_STATUS_REJECTED = 9
ORDER_STATUS_EXPIRED = 10


class OrderRequest(_message.Message):
    """OrderRequest protobuf message stub."""

    DESCRIPTOR = None

    def __init__(
        self,
        client_order_id: str = "",
        strategy_id: str = "",
        symbol: str = "",
        exchange: str = "",
        side: int = 0,
        order_type: int = 0,
        quantity: int = 0,
        limit_price: float = 0.0,
        stop_price: float = 0.0,
        time_in_force: int = 0,
        currency: str = "",
        signal_time=None,
        metadata=None,
        **kwargs,
    ):
        self.client_order_id = client_order_id
        self.strategy_id = strategy_id
        self.symbol = symbol
        self.exchange = exchange
        self.side = side
        self.order_type = order_type
        self.quantity = quantity
        self.limit_price = limit_price
        self.stop_price = stop_price
        self.time_in_force = time_in_force
        self.currency = currency
        self.signal_time = signal_time
        self.metadata = metadata or {}

    def SerializeToString(self) -> bytes:
        raise NotImplementedError("Use protoc-generated code for serialization")

    def ParseFromString(self, data: bytes) -> None:
        raise NotImplementedError("Use protoc-generated code for deserialization")


class RiskDecision(_message.Message):
    """RiskDecision protobuf message stub."""

    DESCRIPTOR = None

    def __init__(
        self,
        client_order_id: str = "",
        status: int = 0,
        rejection_reasons=None,
        approved_quantity: float = 0.0,
        portfolio_var_before: float = 0.0,
        portfolio_var_after: float = 0.0,
        decided_at=None,
        **kwargs,
    ):
        self.client_order_id = client_order_id
        self.status = status
        self.rejection_reasons = rejection_reasons or []
        self.approved_quantity = approved_quantity
        self.portfolio_var_before = portfolio_var_before
        self.portfolio_var_after = portfolio_var_after
        self.decided_at = decided_at

    def SerializeToString(self) -> bytes:
        raise NotImplementedError("Use protoc-generated code for serialization")

    def ParseFromString(self, data: bytes) -> None:
        raise NotImplementedError("Use protoc-generated code for deserialization")


class OrderEvent(_message.Message):
    """OrderEvent protobuf message stub."""

    DESCRIPTOR = None

    def __init__(
        self,
        event_id: str = "",
        client_order_id: str = "",
        broker_order_id: str = "",
        from_status: int = 0,
        to_status: int = 0,
        filled_quantity: float = 0.0,
        filled_price: float = 0.0,
        commission: float = 0.0,
        tax: float = 0.0,
        rejection_reason: str = "",
        occurred_at=None,
        source: str = "",
        **kwargs,
    ):
        self.event_id = event_id
        self.client_order_id = client_order_id
        self.broker_order_id = broker_order_id
        self.from_status = from_status
        self.to_status = to_status
        self.filled_quantity = filled_quantity
        self.filled_price = filled_price
        self.commission = commission
        self.tax = tax
        self.rejection_reason = rejection_reason
        self.occurred_at = occurred_at
        self.source = source

    def SerializeToString(self) -> bytes:
        raise NotImplementedError("Use protoc-generated code for serialization")

    def ParseFromString(self, data: bytes) -> None:
        raise NotImplementedError("Use protoc-generated code for deserialization")
