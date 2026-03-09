"""Auto-generated Protobuf bindings for pre_trade_risk.proto.

Regenerate with: bash scripts/generate_protobuf_python_bindings.sh
"""

from google.protobuf import message as _message

# Enum value constants for RiskLimitType
RISK_LIMIT_TYPE_UNSPECIFIED = 0
RISK_LIMIT_MAX_POSITION_SIZE_PCT = 1
RISK_LIMIT_MAX_SECTOR_CONCENTRATION = 2
RISK_LIMIT_DAILY_LOSS_LIMIT = 3
RISK_LIMIT_MAX_ORDERS_PER_MINUTE = 4
RISK_LIMIT_MAX_GROSS_EXPOSURE = 5
RISK_LIMIT_MAX_VAR = 6
RISK_LIMIT_MIN_LOT_SIZE = 7
RISK_LIMIT_T2_BUYING_POWER = 8


class RiskBreachEvent(_message.Message):
    """RiskBreachEvent protobuf message stub."""

    DESCRIPTOR = None

    def __init__(
        self,
        breach_id: str = "",
        limit_type: int = 0,
        symbol: str = "",
        strategy_id: str = "",
        limit_value: float = 0.0,
        actual_value: float = 0.0,
        action_taken: str = "",
        occurred_at=None,
        **kwargs,
    ):
        self.breach_id = breach_id
        self.limit_type = limit_type
        self.symbol = symbol
        self.strategy_id = strategy_id
        self.limit_value = limit_value
        self.actual_value = actual_value
        self.action_taken = action_taken
        self.occurred_at = occurred_at

    def SerializeToString(self) -> bytes:
        raise NotImplementedError("Use protoc-generated code for serialization")

    def ParseFromString(self, data: bytes) -> None:
        raise NotImplementedError("Use protoc-generated code for deserialization")


class CircuitBreakerState(_message.Message):
    """CircuitBreakerState protobuf message stub."""

    DESCRIPTOR = None

    def __init__(
        self,
        is_halted: bool = False,
        halt_reason: str = "",
        halted_strategies=None,
        halted_at=None,
        auto_resume_at=None,
        **kwargs,
    ):
        self.is_halted = is_halted
        self.halt_reason = halt_reason
        self.halted_strategies = halted_strategies or []
        self.halted_at = halted_at
        self.auto_resume_at = auto_resume_at

    def SerializeToString(self) -> bytes:
        raise NotImplementedError("Use protoc-generated code for serialization")

    def ParseFromString(self, data: bytes) -> None:
        raise NotImplementedError("Use protoc-generated code for deserialization")


# Re-export RiskLimitType as a namespace for enum access
class RiskLimitType:
    """RiskLimitType enum namespace."""

    RISK_LIMIT_TYPE_UNSPECIFIED = 0
    RISK_LIMIT_MAX_POSITION_SIZE_PCT = 1
    RISK_LIMIT_MAX_SECTOR_CONCENTRATION = 2
    RISK_LIMIT_DAILY_LOSS_LIMIT = 3
    RISK_LIMIT_MAX_ORDERS_PER_MINUTE = 4
    RISK_LIMIT_MAX_GROSS_EXPOSURE = 5
    RISK_LIMIT_MAX_VAR = 6
    RISK_LIMIT_MIN_LOT_SIZE = 7
    RISK_LIMIT_T2_BUYING_POWER = 8
