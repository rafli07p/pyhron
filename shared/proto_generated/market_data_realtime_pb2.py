"""Auto-generated Protobuf bindings for market_data_realtime.proto.

Regenerate with: bash scripts/generate_protobuf_python_bindings.sh
"""

from google.protobuf import message as _message


class OHLCVBar(_message.Message):
    """OHLCVBar protobuf message stub."""

    DESCRIPTOR = None

    def __init__(
        self,
        symbol: str = "",
        exchange: str = "",
        interval: str = "",
        open: float = 0.0,
        high: float = 0.0,
        low: float = 0.0,
        close: float = 0.0,
        adjusted_close: float = 0.0,
        volume: int = 0,
        vwap: float = 0.0,
        bar_time=None,
        **kwargs,
    ):
        self.symbol = symbol
        self.exchange = exchange
        self.interval = interval
        self.open = open
        self.high = high
        self.low = low
        self.close = close
        self.adjusted_close = adjusted_close
        self.volume = volume
        self.vwap = vwap
        self.bar_time = bar_time

    def SerializeToString(self) -> bytes:
        raise NotImplementedError("Use protoc-generated code for serialization")

    def ParseFromString(self, data: bytes) -> None:
        raise NotImplementedError("Use protoc-generated code for deserialization")


class Tick(_message.Message):
    """Tick protobuf message stub."""

    DESCRIPTOR = None

    def __init__(
        self,
        symbol: str = "",
        exchange: str = "",
        bid: float = 0.0,
        ask: float = 0.0,
        last: float = 0.0,
        volume: int = 0,
        tick_time=None,
        **kwargs,
    ):
        self.symbol = symbol
        self.exchange = exchange
        self.bid = bid
        self.ask = ask
        self.last = last
        self.volume = volume
        self.tick_time = tick_time

    def SerializeToString(self) -> bytes:
        raise NotImplementedError("Use protoc-generated code for serialization")

    def ParseFromString(self, data: bytes) -> None:
        raise NotImplementedError("Use protoc-generated code for deserialization")
