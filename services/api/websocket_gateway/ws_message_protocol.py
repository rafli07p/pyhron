"""WebSocket message protocol types for the Pyhron real-time feed.

All messages between server and client are JSON with a mandatory ``type``
field.  All numeric values are serialised as **strings** to preserve
``Decimal`` precision.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime


def _now_iso() -> str:
    return datetime.now(UTC).isoformat()


# ---------------------------------------------------------------------------
# Client → Server
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class AuthMessage:
    type: str = "AUTH"
    token: str = ""


@dataclass(frozen=True)
class SubscribeMessage:
    type: str = "SUBSCRIBE"
    channel: str = ""
    key: str = ""


@dataclass(frozen=True)
class UnsubscribeMessage:
    type: str = "UNSUBSCRIBE"
    channel: str = ""
    key: str = ""


@dataclass(frozen=True)
class PongMessage:
    type: str = "PONG"
    timestamp: str = ""


# ---------------------------------------------------------------------------
# Server → Client
# ---------------------------------------------------------------------------


@dataclass
class AuthOkMessage:
    type: str = "AUTH_OK"
    user_id: str = ""
    username: str = ""
    role: str = ""
    server_time: str = field(default_factory=_now_iso)

    def to_dict(self) -> dict[str, str]:
        return asdict(self)


@dataclass
class AuthFailMessage:
    type: str = "AUTH_FAIL"
    reason: str = ""

    def to_dict(self) -> dict[str, str]:
        return asdict(self)


@dataclass
class SubscribedMessage:
    type: str = "SUBSCRIBED"
    channel: str = ""
    key: str = ""

    def to_dict(self) -> dict[str, str]:
        return asdict(self)


@dataclass
class HeartbeatMessage:
    type: str = "HEARTBEAT"
    server_time: str = field(default_factory=_now_iso)
    connection_id: str = ""

    def to_dict(self) -> dict[str, str]:
        return asdict(self)


@dataclass
class ErrorMessage:
    type: str = "ERROR"
    code: str = ""
    message: str = ""

    def to_dict(self) -> dict[str, str]:
        return asdict(self)


@dataclass
class QuoteUpdateMessage:
    type: str = "QUOTE_UPDATE"
    symbol: str = ""
    timestamp: str = ""
    open: str = ""
    high: str = ""
    low: str = ""
    close: str = ""
    volume: str = ""
    value_idr: str = ""
    change: str = ""
    change_pct: str = ""
    prev_close: str = ""
    bid: str = ""
    ask: str = ""
    bid_volume: str = ""
    ask_volume: str = ""

    def to_dict(self) -> dict[str, str]:
        return asdict(self)


@dataclass
class OrderUpdateMessage:
    type: str = "ORDER_UPDATE"
    order_id: str = ""
    client_order_id: str = ""
    symbol: str = ""
    side: str = ""
    order_type: str = ""
    status: str = ""
    quantity_lots: int = 0
    filled_quantity_lots: int = 0
    limit_price: str = ""
    avg_fill_price: str = ""
    commission_idr: str = ""
    submitted_at: str = ""
    filled_at: str = ""
    updated_at: str = ""

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass
class PositionUpdateMessage:
    type: str = "POSITION_UPDATE"
    symbol: str = ""
    quantity_lots: int = 0
    avg_cost_idr: str = ""
    last_price: str = ""
    unrealized_pnl_idr: str = ""
    unrealized_pnl_pct: str = ""
    realized_pnl_idr: str = ""
    updated_at: str = ""

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass
class SignalUpdateMessage:
    type: str = "SIGNAL_UPDATE"
    strategy_id: str = ""
    symbol: str = ""
    signal_type: str = ""
    alpha_score: str = ""
    target_weight: str = ""
    target_lots: int = 0
    rank: int = 0
    universe_size: int = 0
    generated_at: str = ""

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass
class MarketStatusMessage:
    type: str = "MARKET_STATUS"
    status: str = ""
    session: str = ""
    next_event: str = ""
    next_event_at: str = ""
    ihsg_last: str = ""
    ihsg_change_pct: str = ""
    server_time: str = field(default_factory=_now_iso)

    def to_dict(self) -> dict[str, str]:
        return asdict(self)
