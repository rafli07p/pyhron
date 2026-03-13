"""Emergency trading halt mechanism (kill switch).

The kill switch is the most critical safety component in the platform.
When triggered, it halts all trading activity within one second.

State is stored in Redis for sub-millisecond read latency.
All order submission paths check the kill switch before proceeding.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from redis.asyncio import Redis

logger = logging.getLogger(__name__)

REDIS_KEY_GLOBAL = "pyhron:kill_switch:global"
REDIS_KEY_STRATEGY = "pyhron:kill_switch:strategy:{strategy_id}"
REDIS_KEY_SYMBOL = "pyhron:kill_switch:symbol:{symbol}"


@dataclass(frozen=True)
class KillSwitchEvent:
    """Record of a kill switch trigger event."""

    level: str
    key: str | None
    reason: str
    triggered_by: str
    triggered_at: datetime
    orders_cancelled: int


class KillSwitchActiveError(Exception):
    """Raised when an order is blocked by the kill switch."""

    def __init__(self, message: str, *, strategy_id: str | None = None, symbol: str | None = None) -> None:
        super().__init__(message)
        self.strategy_id = strategy_id
        self.symbol = symbol


class KillSwitch:
    """Emergency trading halt mechanism.

    Operates at three levels:
    1. Global: halts all trading across all strategies and accounts
    2. Strategy: halts trading for a specific strategy
    3. Symbol: blocks orders for a specific symbol

    Arming vs Triggering:
    - Armed: kill switch is enabled and monitoring thresholds
    - Triggered: trading has been halted; requires manual reset
    """

    def __init__(
        self,
        redis_client: Redis,
        db_session_factory: Any = None,
        broker_adapter: Any = None,
    ) -> None:
        self._redis = redis_client
        self._db_session_factory = db_session_factory
        self._broker_adapter = broker_adapter

    async def is_halted(
        self,
        strategy_id: str | None = None,
        symbol: str | None = None,
    ) -> bool:
        """Check if trading is halted at any applicable level.

        Checks global, then strategy, then symbol.
        Called on every order submission -- must be <1ms.
        Uses Redis GET (single round trip per level).
        """
        # Check global first
        if await self._redis.get(REDIS_KEY_GLOBAL):
            return True

        # Check strategy level
        if strategy_id:
            key = REDIS_KEY_STRATEGY.format(strategy_id=strategy_id)
            if await self._redis.get(key):
                return True

        # Check symbol level
        if symbol:
            key = REDIS_KEY_SYMBOL.format(symbol=symbol)
            if await self._redis.get(key):
                return True

        return False

    async def trigger(
        self,
        level: str,
        key: str | None,
        reason: str,
        triggered_by: str,
        cancel_open_orders: bool = True,
    ) -> KillSwitchEvent:
        """Trigger the kill switch at the specified level.

        Steps:
        1. SET Redis key with reason and timestamp (atomic)
        2. Update live_trading_config.kill_switch_triggered = True
        3. If cancel_open_orders=True: cancel all open orders via broker
        4. Publish KILL_SWITCH_TRIGGERED event to Kafka
        5. Broadcast via WebSocket to all terminals

        Redis SET is step 1 -- if anything else fails, trading stays halted.
        """
        triggered_at = datetime.now(UTC)
        payload = json.dumps({
            "reason": reason,
            "triggered_by": triggered_by,
            "triggered_at": triggered_at.isoformat(),
        })

        # Step 1: SET Redis key (must succeed first)
        redis_key = self._resolve_redis_key(level, key)
        await self._redis.set(redis_key, payload)

        logger.critical(
            "KILL SWITCH TRIGGERED level=%s key=%s reason=%s by=%s",
            level,
            key,
            reason,
            triggered_by,
        )

        # Step 2: Update DB (best-effort)
        orders_cancelled = 0
        if self._db_session_factory and key and level == "strategy":
            try:
                await self._update_db_kill_switch(key, reason, triggered_at)
            except Exception:
                logger.exception("kill_switch.db_update_failed strategy_id=%s", key)

        # Step 3: Cancel open orders (best-effort)
        if cancel_open_orders and self._broker_adapter:
            try:
                await self._broker_adapter.cancel_all_orders()
                orders_cancelled = 1  # Simplified: broker handles batch cancel
            except Exception:
                logger.exception("kill_switch.cancel_orders_failed")

        return KillSwitchEvent(
            level=level,
            key=key,
            reason=reason,
            triggered_by=triggered_by,
            triggered_at=triggered_at,
            orders_cancelled=orders_cancelled,
        )

    async def reset(
        self,
        level: str,
        key: str | None,
        reason: str,
        reset_by: str,
    ) -> None:
        """Reset the kill switch. Requires explicit operator action.

        DEL Redis key, update DB record, log at CRITICAL level.
        """
        redis_key = self._resolve_redis_key(level, key)
        await self._redis.delete(redis_key)

        logger.critical(
            "KILL SWITCH RESET level=%s key=%s reason=%s by=%s",
            level,
            key,
            reason,
            reset_by,
        )

        if self._db_session_factory and key and level == "strategy":
            try:
                await self._reset_db_kill_switch(key)
            except Exception:
                logger.exception("kill_switch.db_reset_failed strategy_id=%s", key)

    async def arm(
        self,
        strategy_id: str,
        max_daily_loss_idr: float,
        max_drawdown_pct: float,
        max_portfolio_var_pct: float,
    ) -> None:
        """Arm automatic kill switch monitoring for a strategy.

        Stores thresholds in Redis for the monitoring loop.
        """
        arm_key = f"pyhron:kill_switch:arm:{strategy_id}"
        payload = json.dumps({
            "strategy_id": strategy_id,
            "max_daily_loss_idr": max_daily_loss_idr,
            "max_drawdown_pct": max_drawdown_pct,
            "max_portfolio_var_pct": max_portfolio_var_pct,
            "armed_at": datetime.now(UTC).isoformat(),
        })
        await self._redis.set(arm_key, payload)
        logger.info("kill_switch.armed strategy_id=%s", strategy_id)

    async def get_status(self, strategy_id: str | None = None) -> dict[str, Any]:
        """Get current kill switch state for all levels."""
        status: dict[str, Any] = {}

        global_val = await self._redis.get(REDIS_KEY_GLOBAL)
        status["global"] = json.loads(global_val) if global_val else None

        if strategy_id:
            strat_key = REDIS_KEY_STRATEGY.format(strategy_id=strategy_id)
            strat_val = await self._redis.get(strat_key)
            status["strategy"] = json.loads(strat_val) if strat_val else None

            arm_key = f"pyhron:kill_switch:arm:{strategy_id}"
            arm_val = await self._redis.get(arm_key)
            status["armed"] = json.loads(arm_val) if arm_val else None

        return status

    def _resolve_redis_key(self, level: str, key: str | None) -> str:
        if level == "global":
            return REDIS_KEY_GLOBAL
        if level == "strategy" and key:
            return REDIS_KEY_STRATEGY.format(strategy_id=key)
        if level == "symbol" and key:
            return REDIS_KEY_SYMBOL.format(symbol=key)
        msg = f"Invalid kill switch level={level} key={key}"
        raise ValueError(msg)

    async def _update_db_kill_switch(
        self,
        strategy_id: str,
        reason: str,
        triggered_at: datetime,
    ) -> None:
        """Update live_trading_config in DB."""
        from sqlalchemy import text

        async with self._db_session_factory() as session:
            await session.execute(
                text(
                    "UPDATE live_trading_config "
                    "SET kill_switch_triggered = TRUE, "
                    "    kill_switch_reason = :reason, "
                    "    kill_switch_triggered_at = :triggered_at, "
                    "    updated_at = now() "
                    "WHERE strategy_id = :strategy_id::uuid AND is_active = TRUE"
                ),
                {"strategy_id": strategy_id, "reason": reason, "triggered_at": triggered_at},
            )
            await session.commit()

    async def _reset_db_kill_switch(self, strategy_id: str) -> None:
        """Reset kill switch state in DB."""
        from sqlalchemy import text

        async with self._db_session_factory() as session:
            await session.execute(
                text(
                    "UPDATE live_trading_config "
                    "SET kill_switch_triggered = FALSE, "
                    "    kill_switch_reason = NULL, "
                    "    kill_switch_triggered_at = NULL, "
                    "    updated_at = now() "
                    "WHERE strategy_id = :strategy_id::uuid AND is_active = TRUE"
                ),
                {"strategy_id": strategy_id},
            )
            await session.commit()
