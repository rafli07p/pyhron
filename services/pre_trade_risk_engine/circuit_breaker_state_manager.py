"""Circuit breaker state manager with Redis-backed halt/resume.

Manages trading circuit breakers that halt order submission for specific
strategies or exchanges when risk limits are breached. State is persisted
in Redis for cross-service visibility and automatic expiry.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from enum import StrEnum

from shared.redis_cache_client import get_redis
from shared.structured_json_logger import get_logger

logger = get_logger(__name__)

# Redis key patterns
CIRCUIT_BREAKER_KEY = "pyhron:risk:circuit_breaker:{entity_id}"
CIRCUIT_BREAKER_HISTORY_KEY = "pyhron:risk:circuit_breaker_history:{entity_id}"

# Default TTL for circuit breaker keys
DEFAULT_TTL_SECONDS: int = 3600  # 1 hour
MAX_HISTORY_ENTRIES: int = 100


class CircuitBreakerReason(StrEnum):
    """Reason codes for circuit breaker activation."""

    DAILY_LOSS_LIMIT = "DAILY_LOSS_LIMIT"
    POSITION_MISMATCH = "POSITION_MISMATCH"
    VAR_BREACH = "VAR_BREACH"
    MANUAL_HALT = "MANUAL_HALT"
    CONNECTIVITY_FAILURE = "CONNECTIVITY_FAILURE"
    EXCHANGE_HALT = "EXCHANGE_HALT"


@dataclass(frozen=True)
class CircuitBreakerState:
    """Current state of a circuit breaker.

    Attributes:
        entity_id: The strategy or exchange identifier.
        is_active: Whether the circuit breaker is currently tripped.
        reason: The reason code for activation, if active.
        detail: Human-readable detail about the activation.
        activated_at: Timestamp when the breaker was activated.
        ttl_seconds: Remaining TTL in seconds before auto-reset.
    """

    entity_id: str
    is_active: bool
    reason: CircuitBreakerReason | None = None
    detail: str = ""
    activated_at: str = ""
    ttl_seconds: int = 0


class CircuitBreakerStateManager:
    """Manages Redis-backed circuit breakers for trading halt/resume.

    Each circuit breaker is identified by an ``entity_id`` which can be
    a strategy ID, exchange name, or any other grouping key. When a
    breaker is tripped, a Redis key is set with an expiry TTL. The risk
    engine checks this key before processing each signal.

    Supports:
      - Halt: Trip a circuit breaker with a reason and optional TTL.
      - Resume: Manually clear a circuit breaker before TTL expiry.
      - Query: Check whether a specific breaker is active.
      - History: Maintain a log of recent activations for auditing.

    Usage::

        manager = CircuitBreakerStateManager()
        await manager.halt(
            entity_id="strategy-alpha",
            reason=CircuitBreakerReason.DAILY_LOSS_LIMIT,
            detail="Daily loss -3.2% exceeds limit -2.5%",
        )
        state = await manager.get_state("strategy-alpha")
        assert state.is_active
        await manager.resume("strategy-alpha")
    """

    def __init__(self, default_ttl_seconds: int = DEFAULT_TTL_SECONDS) -> None:
        """Initialize the circuit breaker manager.

        Args:
            default_ttl_seconds: Default TTL for circuit breaker keys
                before automatic reset.
        """
        self._default_ttl: int = default_ttl_seconds

    async def halt(
        self,
        entity_id: str,
        reason: CircuitBreakerReason,
        detail: str = "",
        ttl_seconds: int | None = None,
    ) -> CircuitBreakerState:
        """Trip a circuit breaker, halting trading for the given entity.

        Sets a Redis key with the breaker reason and expiry. Also appends
        an entry to the activation history list.

        Args:
            entity_id: The strategy or exchange identifier to halt.
            reason: The reason code for the halt.
            detail: Optional human-readable detail string.
            ttl_seconds: Override TTL in seconds. Uses default if None.

        Returns:
            The resulting CircuitBreakerState.
        """
        redis = await get_redis()
        ttl = ttl_seconds if ttl_seconds is not None else self._default_ttl
        now = datetime.now(tz=UTC)

        cb_key = CIRCUIT_BREAKER_KEY.format(entity_id=entity_id)
        value = f"{reason.value}:{detail}:{now.isoformat()}"

        await redis.set(cb_key, value, ex=ttl)

        # Append to history
        history_key = CIRCUIT_BREAKER_HISTORY_KEY.format(entity_id=entity_id)
        history_entry = f"{now.isoformat()}|HALT|{reason.value}|{detail}"
        await redis.lpush(history_key, history_entry)
        await redis.ltrim(history_key, 0, MAX_HISTORY_ENTRIES - 1)

        state = CircuitBreakerState(
            entity_id=entity_id,
            is_active=True,
            reason=reason,
            detail=detail,
            activated_at=now.isoformat(),
            ttl_seconds=ttl,
        )

        logger.critical(
            "circuit_breaker_halted",
            entity_id=entity_id,
            reason=reason.value,
            detail=detail,
            ttl_seconds=ttl,
        )

        return state

    async def resume(self, entity_id: str, reason: str = "manual_resume") -> bool:
        """Clear a circuit breaker, resuming trading for the given entity.

        Deletes the Redis key and logs the resume event to the history.

        Args:
            entity_id: The strategy or exchange identifier to resume.
            reason: A reason string for the resume action (for auditing).

        Returns:
            True if a circuit breaker was active and cleared, False if
            no active breaker existed.
        """
        redis = await get_redis()
        cb_key = CIRCUIT_BREAKER_KEY.format(entity_id=entity_id)

        existed = await redis.delete(cb_key)

        # Log to history
        now = datetime.now(tz=UTC)
        history_key = CIRCUIT_BREAKER_HISTORY_KEY.format(entity_id=entity_id)
        history_entry = f"{now.isoformat()}|RESUME|{reason}|"
        await redis.lpush(history_key, history_entry)
        await redis.ltrim(history_key, 0, MAX_HISTORY_ENTRIES - 1)

        if existed:
            logger.info(
                "circuit_breaker_resumed",
                entity_id=entity_id,
                reason=reason,
            )
            return True

        logger.debug(
            "circuit_breaker_resume_no_active_breaker",
            entity_id=entity_id,
        )
        return False

    async def is_halted(self, entity_id: str) -> bool:
        """Check whether a circuit breaker is currently active.

        Args:
            entity_id: The strategy or exchange identifier to check.

        Returns:
            True if the circuit breaker is active, False otherwise.
        """
        redis = await get_redis()
        cb_key = CIRCUIT_BREAKER_KEY.format(entity_id=entity_id)
        value = await redis.get(cb_key)
        return value is not None

    async def get_state(self, entity_id: str) -> CircuitBreakerState:
        """Get the full state of a circuit breaker.

        Args:
            entity_id: The strategy or exchange identifier.

        Returns:
            A CircuitBreakerState with current activation details.
        """
        redis = await get_redis()
        cb_key = CIRCUIT_BREAKER_KEY.format(entity_id=entity_id)
        value = await redis.get(cb_key)

        if value is None:
            return CircuitBreakerState(
                entity_id=entity_id,
                is_active=False,
            )

        # Parse the stored value: "REASON:detail:timestamp"
        parts = value.split(":", 2) if isinstance(value, str) else value.decode().split(":", 2)
        reason_str = parts[0] if len(parts) > 0 else ""
        detail = parts[1] if len(parts) > 1 else ""
        activated_at = parts[2] if len(parts) > 2 else ""

        ttl = await redis.ttl(cb_key)

        try:
            reason = CircuitBreakerReason(reason_str)
        except ValueError:
            reason = CircuitBreakerReason.MANUAL_HALT

        return CircuitBreakerState(
            entity_id=entity_id,
            is_active=True,
            reason=reason,
            detail=detail,
            activated_at=activated_at,
            ttl_seconds=max(0, ttl),
        )

    async def get_history(self, entity_id: str, limit: int = 20) -> list[dict[str, str]]:
        """Retrieve recent circuit breaker activation history.

        Args:
            entity_id: The strategy or exchange identifier.
            limit: Maximum number of history entries to return.

        Returns:
            List of history entry dicts with timestamp, action, reason,
            and detail fields, ordered most recent first.
        """
        redis = await get_redis()
        history_key = CIRCUIT_BREAKER_HISTORY_KEY.format(entity_id=entity_id)
        entries = await redis.lrange(history_key, 0, limit - 1)

        results: list[dict[str, str]] = []
        for entry in entries or []:
            entry_str = entry if isinstance(entry, str) else entry.decode()
            parts = entry_str.split("|", 3)
            results.append(
                {
                    "timestamp": parts[0] if len(parts) > 0 else "",
                    "action": parts[1] if len(parts) > 1 else "",
                    "reason": parts[2] if len(parts) > 2 else "",
                    "detail": parts[3] if len(parts) > 3 else "",
                }
            )

        return results
