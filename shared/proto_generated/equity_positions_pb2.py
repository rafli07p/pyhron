"""Auto-generated Protobuf bindings for equity_positions.proto.

Regenerate with: bash scripts/generate_protobuf_python_bindings.sh
"""

from google.protobuf import message as _message


class Position(_message.Message):
    """Position protobuf message stub."""

    DESCRIPTOR = None

    def __init__(
        self,
        symbol: str = "",
        exchange: str = "",
        strategy_id: str = "",
        quantity: int = 0,
        avg_entry_price: float = 0.0,
        current_price: float = 0.0,
        unrealized_pnl: float = 0.0,
        realized_pnl: float = 0.0,
        market_value: float = 0.0,
        last_updated=None,
        **kwargs,
    ):
        self.symbol = symbol
        self.exchange = exchange
        self.strategy_id = strategy_id
        self.quantity = quantity
        self.avg_entry_price = avg_entry_price
        self.current_price = current_price
        self.unrealized_pnl = unrealized_pnl
        self.realized_pnl = realized_pnl
        self.market_value = market_value
        self.last_updated = last_updated

    def SerializeToString(self) -> bytes:
        raise NotImplementedError("Use protoc-generated code for serialization")

    def ParseFromString(self, data: bytes) -> None:
        raise NotImplementedError("Use protoc-generated code for deserialization")


class PositionEvent(_message.Message):
    """PositionEvent protobuf message stub."""

    DESCRIPTOR = None

    def __init__(
        self,
        event_id: str = "",
        symbol: str = "",
        strategy_id: str = "",
        triggering_order_id: str = "",
        quantity_delta: float = 0.0,
        execution_price: float = 0.0,
        realized_pnl_delta: float = 0.0,
        commission: float = 0.0,
        tax: float = 0.0,
        occurred_at=None,
        **kwargs,
    ):
        self.event_id = event_id
        self.symbol = symbol
        self.strategy_id = strategy_id
        self.triggering_order_id = triggering_order_id
        self.quantity_delta = quantity_delta
        self.execution_price = execution_price
        self.realized_pnl_delta = realized_pnl_delta
        self.commission = commission
        self.tax = tax
        self.occurred_at = occurred_at

    def SerializeToString(self) -> bytes:
        raise NotImplementedError("Use protoc-generated code for serialization")

    def ParseFromString(self, data: bytes) -> None:
        raise NotImplementedError("Use protoc-generated code for deserialization")


class PortfolioSnapshot(_message.Message):
    """PortfolioSnapshot protobuf message stub."""

    DESCRIPTOR = None

    def __init__(
        self,
        portfolio_id: str = "",
        positions=None,
        total_market_value: float = 0.0,
        cash_balance: float = 0.0,
        total_unrealized_pnl: float = 0.0,
        total_realized_pnl_today: float = 0.0,
        portfolio_var_95: float = 0.0,
        snapshot_at=None,
        **kwargs,
    ):
        self.portfolio_id = portfolio_id
        self.positions = positions or []
        self.total_market_value = total_market_value
        self.cash_balance = cash_balance
        self.total_unrealized_pnl = total_unrealized_pnl
        self.total_realized_pnl_today = total_realized_pnl_today
        self.portfolio_var_95 = portfolio_var_95
        self.snapshot_at = snapshot_at

    def SerializeToString(self) -> bytes:
        raise NotImplementedError("Use protoc-generated code for serialization")

    def ParseFromString(self, data: bytes) -> None:
        raise NotImplementedError("Use protoc-generated code for deserialization")
