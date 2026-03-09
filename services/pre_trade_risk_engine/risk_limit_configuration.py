"""Per-strategy risk limit configuration.

Provides a structured way to define, load, and query risk limits for
individual strategies. Supports defaults with per-strategy overrides
loaded from the database or configuration.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from sqlalchemy import text

from shared.async_database_session import get_session
from shared.configuration_settings import get_config
from shared.structured_json_logger import get_logger

logger = get_logger(__name__)


@dataclass
class StrategyRiskLimits:
    """Risk limit definitions for a single strategy.

    Attributes:
        strategy_id: The strategy identifier.
        max_position_size_pct: Maximum single-position size as a fraction
            of portfolio value.
        max_sector_concentration_pct: Maximum sector exposure as a fraction
            of portfolio value.
        daily_loss_limit_pct: Maximum daily loss before circuit breaker
            triggers, as a fraction.
        max_var_95_pct: Maximum 95% VaR as a fraction of portfolio value.
        idx_lot_size: IDX lot size constraint (default 100 shares).
        max_order_value: Maximum value of a single order in currency units.
        max_daily_orders: Maximum number of orders per day.
        max_signal_age_seconds: Maximum allowed signal age before rejection.
        enabled: Whether this strategy is enabled for trading.
    """

    strategy_id: str
    max_position_size_pct: float = 0.10
    max_sector_concentration_pct: float = 0.25
    daily_loss_limit_pct: float = 0.02
    max_var_95_pct: float = 0.05
    idx_lot_size: int = 100
    max_order_value: float = 0.0  # 0 = unlimited
    max_daily_orders: int = 0  # 0 = unlimited
    max_signal_age_seconds: int = 300
    enabled: bool = True


# Default limits applied when no strategy-specific override exists
DEFAULT_LIMITS = StrategyRiskLimits(strategy_id="__default__")


class RiskLimitConfiguration:
    """Manages per-strategy risk limit definitions.

    Loads strategy-specific risk limits from the database and provides
    a fallback to global defaults from the application configuration.
    Caches loaded limits in memory for fast access during risk evaluation.

    Usage::

        config = RiskLimitConfiguration()
        await config.load()
        limits = config.get_limits("strategy-alpha")
        print(limits.max_position_size_pct)  # 0.10
    """

    def __init__(self) -> None:
        self._strategy_limits: dict[str, StrategyRiskLimits] = {}
        self._default_limits: StrategyRiskLimits = DEFAULT_LIMITS
        self._loaded: bool = False

    async def load(self) -> None:
        """Load risk limits from the application config and database.

        First applies global defaults from the app config, then loads
        any per-strategy overrides from the ``strategy_risk_limits`` table.
        """
        self._load_defaults_from_config()
        await self._load_strategy_overrides()
        self._loaded = True
        logger.info(
            "risk_limits_loaded",
            strategies_with_overrides=len(self._strategy_limits),
        )

    def _load_defaults_from_config(self) -> None:
        """Load global default limits from the application configuration."""
        config = get_config()
        self._default_limits = StrategyRiskLimits(
            strategy_id="__default__",
            max_position_size_pct=getattr(config, "risk_max_position_size_pct", 0.10),
            max_sector_concentration_pct=getattr(config, "risk_max_sector_concentration_pct", 0.25),
            daily_loss_limit_pct=getattr(config, "risk_daily_loss_limit_pct", 0.02),
            max_var_95_pct=getattr(config, "risk_max_var_95_pct", 0.05),
            idx_lot_size=getattr(config, "risk_idx_lot_size", 100),
        )

    async def _load_strategy_overrides(self) -> None:
        """Load per-strategy risk limit overrides from the database.

        Reads from the ``strategy_risk_limits`` table. Each row overrides
        specific fields for a given strategy_id.
        """
        try:
            async with get_session() as session:
                result = await session.execute(
                    text(
                        "SELECT strategy_id, max_position_size_pct, "
                        "max_sector_concentration_pct, daily_loss_limit_pct, "
                        "max_var_95_pct, idx_lot_size, max_order_value, "
                        "max_daily_orders, max_signal_age_seconds, enabled "
                        "FROM strategy_risk_limits WHERE is_active = true"
                    )
                )
                rows = result.fetchall()

                for row in rows:
                    limits = StrategyRiskLimits(
                        strategy_id=row[0],
                        max_position_size_pct=float(row[1]) if row[1] is not None else self._default_limits.max_position_size_pct,
                        max_sector_concentration_pct=float(row[2]) if row[2] is not None else self._default_limits.max_sector_concentration_pct,
                        daily_loss_limit_pct=float(row[3]) if row[3] is not None else self._default_limits.daily_loss_limit_pct,
                        max_var_95_pct=float(row[4]) if row[4] is not None else self._default_limits.max_var_95_pct,
                        idx_lot_size=int(row[5]) if row[5] is not None else self._default_limits.idx_lot_size,
                        max_order_value=float(row[6]) if row[6] is not None else 0.0,
                        max_daily_orders=int(row[7]) if row[7] is not None else 0,
                        max_signal_age_seconds=int(row[8]) if row[8] is not None else 300,
                        enabled=bool(row[9]) if row[9] is not None else True,
                    )
                    self._strategy_limits[limits.strategy_id] = limits

        except Exception:
            logger.warning(
                "strategy_risk_limits_table_not_available",
                message="Using default limits for all strategies",
            )

    def get_limits(self, strategy_id: str) -> StrategyRiskLimits:
        """Get risk limits for a specific strategy.

        Returns strategy-specific overrides if available, otherwise
        returns the global default limits with the strategy_id set.

        Args:
            strategy_id: The strategy identifier.

        Returns:
            The applicable StrategyRiskLimits for this strategy.
        """
        if strategy_id in self._strategy_limits:
            return self._strategy_limits[strategy_id]

        # Return defaults with the correct strategy_id
        return StrategyRiskLimits(
            strategy_id=strategy_id,
            max_position_size_pct=self._default_limits.max_position_size_pct,
            max_sector_concentration_pct=self._default_limits.max_sector_concentration_pct,
            daily_loss_limit_pct=self._default_limits.daily_loss_limit_pct,
            max_var_95_pct=self._default_limits.max_var_95_pct,
            idx_lot_size=self._default_limits.idx_lot_size,
        )

    def set_limits(self, limits: StrategyRiskLimits) -> None:
        """Set or update risk limits for a strategy in the in-memory cache.

        Does not persist to the database. Use for testing or runtime
        overrides that do not need persistence.

        Args:
            limits: The StrategyRiskLimits to cache.
        """
        self._strategy_limits[limits.strategy_id] = limits
        logger.info(
            "risk_limits_updated_in_memory",
            strategy_id=limits.strategy_id,
        )

    def get_all_strategies(self) -> list[str]:
        """Get a list of all strategy IDs with custom risk limits.

        Returns:
            List of strategy ID strings.
        """
        return list(self._strategy_limits.keys())

    @property
    def default_limits(self) -> StrategyRiskLimits:
        """The global default risk limits.

        Returns:
            The default StrategyRiskLimits instance.
        """
        return self._default_limits
