"""Type stubs for strategy_signals_pb2 generated protobuf module."""

from typing import Any

from google.protobuf import timestamp_pb2 as _timestamp_pb2

DESCRIPTOR: Any

class _SignalDirection:
    SIGNAL_DIRECTION_UNSPECIFIED: int
    SIGNAL_DIRECTION_LONG: int
    SIGNAL_DIRECTION_SHORT: int
    SIGNAL_DIRECTION_CLOSE: int
    SIGNAL_DIRECTION_REBALANCE: int

SignalDirection: _SignalDirection

SIGNAL_DIRECTION_UNSPECIFIED: int
SIGNAL_DIRECTION_LONG: int
SIGNAL_DIRECTION_SHORT: int
SIGNAL_DIRECTION_CLOSE: int
SIGNAL_DIRECTION_REBALANCE: int

class Signal:
    DESCRIPTOR: Any
    signal_id: str
    strategy_id: str
    symbol: str
    exchange: str
    direction: int
    target_weight: float
    confidence: float
    signal_type: str
    generated_at: _timestamp_pb2.Timestamp
    valid_until: _timestamp_pb2.Timestamp
    def __init__(
        self,
        *,
        signal_id: str = ...,
        strategy_id: str = ...,
        symbol: str = ...,
        exchange: str = ...,
        direction: int = ...,
        target_weight: float = ...,
        confidence: float = ...,
        signal_type: str = ...,
    ) -> None: ...
