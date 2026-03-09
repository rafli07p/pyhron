"""Auto-generated Protobuf bindings for strategy_signals.proto.

Regenerate with: bash scripts/generate_protobuf_python_bindings.sh
"""

from google.protobuf import message as _message

# Enum value constants for SignalDirection
SIGNAL_DIRECTION_UNSPECIFIED = 0
SIGNAL_DIRECTION_LONG = 1
SIGNAL_DIRECTION_SHORT = 2
SIGNAL_DIRECTION_CLOSE = 3
SIGNAL_DIRECTION_REBALANCE = 4


class Signal(_message.Message):
    """Signal protobuf message stub."""

    DESCRIPTOR = None

    def __init__(
        self,
        signal_id: str = "",
        strategy_id: str = "",
        symbol: str = "",
        exchange: str = "",
        direction: int = 0,
        target_weight: float = 0.0,
        confidence: float = 0.0,
        signal_type: str = "",
        factor_values=None,
        generated_at=None,
        valid_until=None,
        **kwargs,
    ):
        self.signal_id = signal_id
        self.strategy_id = strategy_id
        self.symbol = symbol
        self.exchange = exchange
        self.direction = direction
        self.target_weight = target_weight
        self.confidence = confidence
        self.signal_type = signal_type
        self.factor_values = factor_values or {}
        self.generated_at = generated_at
        self.valid_until = valid_until

    def SerializeToString(self) -> bytes:
        raise NotImplementedError("Use protoc-generated code for serialization")

    def ParseFromString(self, data: bytes) -> None:
        raise NotImplementedError("Use protoc-generated code for deserialization")


class SignalDirection:
    """SignalDirection enum namespace."""

    SIGNAL_DIRECTION_UNSPECIFIED = 0
    SIGNAL_DIRECTION_LONG = 1
    SIGNAL_DIRECTION_SHORT = 2
    SIGNAL_DIRECTION_CLOSE = 3
    SIGNAL_DIRECTION_REBALANCE = 4
