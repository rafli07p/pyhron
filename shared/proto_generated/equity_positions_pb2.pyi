"""Type stubs for equity_positions_pb2 generated protobuf module."""

from typing import Any

DESCRIPTOR: Any

class PositionRecord:
    DESCRIPTOR: Any
    symbol: str
    exchange: str
    strategy_id: str
    quantity: float
    average_entry_price: float
    current_price: float
    unrealized_pnl: float
    realized_pnl: float
    market_value: float
    def __init__(
        self,
        *,
        symbol: str = ...,
        exchange: str = ...,
        strategy_id: str = ...,
        quantity: float = ...,
        average_entry_price: float = ...,
        current_price: float = ...,
        unrealized_pnl: float = ...,
        realized_pnl: float = ...,
        market_value: float = ...,
    ) -> None: ...

class Position:
    DESCRIPTOR: Any
    symbol: str
    exchange: str
    strategy_id: str
    quantity: int
    avg_entry_price: float
    current_price: float
    unrealized_pnl: float
    realized_pnl: float
    market_value: float
    def __init__(
        self,
        *,
        symbol: str = ...,
        exchange: str = ...,
        strategy_id: str = ...,
        quantity: int = ...,
        avg_entry_price: float = ...,
        current_price: float = ...,
        unrealized_pnl: float = ...,
        realized_pnl: float = ...,
        market_value: float = ...,
    ) -> None: ...

class PositionEvent:
    DESCRIPTOR: Any
    event_id: str
    symbol: str
    strategy_id: str
    triggering_order_id: str
    quantity_delta: float
    execution_price: float
    realized_pnl_delta: float
    commission: float
    tax: float
    def __init__(
        self,
        *,
        event_id: str = ...,
        symbol: str = ...,
        strategy_id: str = ...,
        triggering_order_id: str = ...,
        quantity_delta: float = ...,
        execution_price: float = ...,
        realized_pnl_delta: float = ...,
        commission: float = ...,
        tax: float = ...,
    ) -> None: ...

class PortfolioSnapshot:
    DESCRIPTOR: Any
    portfolio_id: str
    positions: list[Position]
    total_market_value: float
    cash_balance: float
    total_unrealized_pnl: float
    total_realized_pnl_today: float
    portfolio_var_95: float
    def __init__(
        self,
        *,
        portfolio_id: str = ...,
        total_market_value: float = ...,
        cash_balance: float = ...,
        total_unrealized_pnl: float = ...,
        total_realized_pnl_today: float = ...,
        portfolio_var_95: float = ...,
    ) -> None: ...
