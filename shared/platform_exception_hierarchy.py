"""Pyhron exception hierarchy.

Every failure path uses a named exception from this module.
No bare ``except:`` anywhere — always specific types.

Hierarchy::

    PyhronError
    ├── ConfigurationError
    ├── DatabaseError
    │   ├── ConnectionError
    │   └── MigrationError
    ├── CacheError
    ├── MessagingError
    │   ├── ProducerError
    │   ├── ConsumerError
    │   └── DeserializationError
    ├── BrokerError
    │   ├── BrokerConnectionError
    │   ├── OrderRejectedError
    │   └── BrokerTimeoutError
    ├── RiskError
    │   ├── RiskCheckFailedError
    │   └── CircuitBreakerOpenError
    ├── OrderError
    │   ├── InvalidTransitionError
    │   ├── DuplicateOrderError
    │   └── OrderNotFoundError
    └── IngestionError
        ├── RateLimitExceededError
        └── DataQualityError
"""

from __future__ import annotations


class PyhronError(Exception):
    """Base exception for all Pyhron platform errors."""

    def __init__(self, message: str, *, context: dict[str, object] | None = None) -> None:
        super().__init__(message)
        self.context = context or {}


# ── Configuration ───────────────────────────────────────────────────────────


class ConfigurationError(PyhronError):
    """Invalid or missing configuration."""


# ── Database ────────────────────────────────────────────────────────────────


class DatabaseError(PyhronError):
    """Database operation failed."""


class DatabaseConnectionError(DatabaseError):
    """Cannot connect to database."""


class MigrationError(DatabaseError):
    """Database migration failed."""


# ── Cache ───────────────────────────────────────────────────────────────────


class CacheError(PyhronError):
    """Redis cache operation failed."""


# ── Messaging ───────────────────────────────────────────────────────────────


class MessagingError(PyhronError):
    """Kafka messaging operation failed."""


class ProducerError(MessagingError):
    """Failed to produce message to Kafka."""


class ConsumerError(MessagingError):
    """Failed to consume message from Kafka."""


class DeserializationError(MessagingError):
    """Failed to deserialize Protobuf message from Kafka."""


# ── Broker ──────────────────────────────────────────────────────────────────


class BrokerError(PyhronError):
    """Broker adapter operation failed."""


class BrokerConnectionError(BrokerError):
    """Cannot connect to broker."""


class OrderRejectedError(BrokerError):
    """Order rejected by broker."""

    def __init__(self, message: str, *, broker_order_id: str = "", reason: str = "") -> None:
        super().__init__(message)
        self.broker_order_id = broker_order_id
        self.reason = reason


class BrokerTimeoutError(BrokerError):
    """Broker operation timed out."""


# ── Risk ────────────────────────────────────────────────────────────────────


class RiskError(PyhronError):
    """Risk engine error."""


class RiskCheckFailedError(RiskError):
    """One or more pre-trade risk checks failed."""

    def __init__(self, message: str, *, reasons: list[str] | None = None) -> None:
        super().__init__(message)
        self.reasons = reasons or []


class CircuitBreakerOpenError(RiskError):
    """Trading halted — circuit breaker is open."""

    def __init__(self, message: str, *, strategy_id: str = "") -> None:
        super().__init__(message)
        self.strategy_id = strategy_id


# ── Order ───────────────────────────────────────────────────────────────────


class OrderError(PyhronError):
    """Order management error."""


class InvalidTransitionError(OrderError):
    """Invalid order state transition."""

    def __init__(
        self, message: str, *, from_status: str = "", to_status: str = ""
    ) -> None:
        super().__init__(message)
        self.from_status = from_status
        self.to_status = to_status


class DuplicateOrderError(OrderError):
    """Order with same client_order_id already exists."""


class OrderNotFoundError(OrderError):
    """Order not found."""


# ── Ingestion ───────────────────────────────────────────────────────────────


class IngestionError(PyhronError):
    """Data ingestion error."""


class RateLimitExceededError(IngestionError):
    """External API rate limit exceeded."""


class DataQualityError(IngestionError):
    """Ingested data failed quality checks."""
