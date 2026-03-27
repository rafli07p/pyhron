"""Message type enumerations for the Pyhron event bus.

Defines canonical message types and priority levels used across all
internal messaging (Kafka topics, Redis streams, WebSocket channels).
Every published event carries a ``MessageType`` so consumers can
route and filter efficiently.
"""

from __future__ import annotations

from enum import IntEnum, StrEnum, unique


@unique
class MessageType(StrEnum):
    """Canonical event / message types used across the platform.

    Naming convention: ``DOMAIN_ACTION`` (e.g. ``ORDER_NEW``).
    """

    # Order lifecycle
    ORDER_NEW = "ORDER_NEW"
    ORDER_ACKNOWLEDGED = "ORDER_ACKNOWLEDGED"
    ORDER_FILL = "ORDER_FILL"
    ORDER_PARTIAL_FILL = "ORDER_PARTIAL_FILL"
    ORDER_CANCEL = "ORDER_CANCEL"
    ORDER_CANCEL_REJECT = "ORDER_CANCEL_REJECT"
    ORDER_REPLACE = "ORDER_REPLACE"
    ORDER_REJECTED = "ORDER_REJECTED"
    ORDER_EXPIRED = "ORDER_EXPIRED"
    ORDER_STATUS = "ORDER_STATUS"

    # Market data
    MARKET_DATA = "MARKET_DATA"
    MARKET_TICK = "MARKET_TICK"
    MARKET_BAR = "MARKET_BAR"
    MARKET_TRADE = "MARKET_TRADE"
    MARKET_QUOTE = "MARKET_QUOTE"
    MARKET_DEPTH = "MARKET_DEPTH"
    MARKET_STATUS = "MARKET_STATUS"

    # Risk & compliance
    RISK_ALERT = "RISK_ALERT"
    RISK_BREACH = "RISK_BREACH"
    RISK_LIMIT_UPDATE = "RISK_LIMIT_UPDATE"
    MARGIN_CALL = "MARGIN_CALL"
    COMPLIANCE_ALERT = "COMPLIANCE_ALERT"

    # Portfolio
    POSITION_UPDATE = "POSITION_UPDATE"
    PNL_UPDATE = "PNL_UPDATE"
    EXPOSURE_UPDATE = "EXPOSURE_UPDATE"
    PORTFOLIO_REBALANCE = "PORTFOLIO_REBALANCE"

    # Research
    BACKTEST_REQUEST = "BACKTEST_REQUEST"
    BACKTEST_RESULT = "BACKTEST_RESULT"
    FACTOR_RESULT = "FACTOR_RESULT"
    SIGNAL_GENERATED = "SIGNAL_GENERATED"

    # System
    HEARTBEAT = "HEARTBEAT"
    SERVICE_UP = "SERVICE_UP"
    SERVICE_DOWN = "SERVICE_DOWN"
    CONFIG_CHANGE = "CONFIG_CHANGE"
    AUDIT_LOG = "AUDIT_LOG"

    # Notifications
    NOTIFICATION_EMAIL = "NOTIFICATION_EMAIL"
    NOTIFICATION_SLACK = "NOTIFICATION_SLACK"
    NOTIFICATION_WEBHOOK = "NOTIFICATION_WEBHOOK"


@unique
class EventPriority(IntEnum):
    """Event processing priority.

    Lower numeric values indicate higher priority.  The OMS and risk
    engine use this to ensure critical events (e.g. margin calls) are
    processed before informational updates.
    """

    CRITICAL = 0
    HIGH = 1
    NORMAL = 2
    LOW = 3
    BACKGROUND = 4

    @property
    def label(self) -> str:
        """Human-readable label for the priority level."""
        return self.name.capitalize()

    def is_urgent(self) -> bool:
        """Return ``True`` for CRITICAL and HIGH priority events."""
        return self.value <= self.HIGH


__all__ = [
    "EventPriority",
    "MessageType",
]
