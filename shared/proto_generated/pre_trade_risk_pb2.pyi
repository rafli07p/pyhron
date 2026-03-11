"""Type stubs for pre_trade_risk_pb2 generated protobuf module."""

from typing import Any

from google.protobuf import timestamp_pb2 as _timestamp_pb2

DESCRIPTOR: Any

class _RiskLimitType:
    RISK_LIMIT_TYPE_UNSPECIFIED: int
    RISK_LIMIT_MAX_POSITION_SIZE_PCT: int
    RISK_LIMIT_MAX_SECTOR_CONCENTRATION: int
    RISK_LIMIT_DAILY_LOSS_LIMIT: int
    RISK_LIMIT_MAX_ORDERS_PER_MINUTE: int
    RISK_LIMIT_MAX_GROSS_EXPOSURE: int
    RISK_LIMIT_MAX_VAR: int
    RISK_LIMIT_MIN_LOT_SIZE: int
    RISK_LIMIT_T2_BUYING_POWER: int

RiskLimitType: _RiskLimitType

RISK_LIMIT_TYPE_UNSPECIFIED: int
RISK_LIMIT_MAX_POSITION_SIZE_PCT: int
RISK_LIMIT_MAX_SECTOR_CONCENTRATION: int
RISK_LIMIT_DAILY_LOSS_LIMIT: int
RISK_LIMIT_MAX_ORDERS_PER_MINUTE: int
RISK_LIMIT_MAX_GROSS_EXPOSURE: int
RISK_LIMIT_MAX_VAR: int
RISK_LIMIT_MIN_LOT_SIZE: int
RISK_LIMIT_T2_BUYING_POWER: int

class RiskBreachEvent:
    DESCRIPTOR: Any
    breach_id: str
    limit_type: int
    symbol: str
    strategy_id: str
    limit_value: float
    actual_value: float
    action_taken: str
    occurred_at: _timestamp_pb2.Timestamp
    def __init__(
        self,
        *,
        breach_id: str = ...,
        limit_type: int = ...,
        symbol: str = ...,
        strategy_id: str = ...,
        limit_value: float = ...,
        actual_value: float = ...,
        action_taken: str = ...,
    ) -> None: ...

class CircuitBreakerState:
    DESCRIPTOR: Any
    is_halted: bool
    halt_reason: str
    halted_strategies: list[str]
    def __init__(
        self,
        *,
        is_halted: bool = ...,
        halt_reason: str = ...,
    ) -> None: ...
