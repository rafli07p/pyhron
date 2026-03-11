"""Trading ORM models — DEPRECATED.

This module is deprecated. Import from ``data_platform.database_models`` instead.

Re-exports canonical model classes for backward compatibility only.
"""

from __future__ import annotations

import warnings

warnings.warn(
    "data_platform.models.trading is deprecated. Use data_platform.database_models instead.",
    DeprecationWarning,
    stacklevel=2,
)

# Re-export canonical models for backward compatibility
from data_platform.database_models.order_lifecycle_record import (
    OrderLifecycleRecord as Order,
)
from data_platform.database_models.order_lifecycle_record import (
    OrderSideEnum,
    OrderStatusEnum,
    OrderTypeEnum,
    TimeInForceEnum,
)
from data_platform.database_models.strategy_position_snapshot import (
    StrategyPositionSnapshot as Position,
)
from data_platform.database_models.strategy_trade_execution_log import (
    StrategyTradeExecutionLog as Trade,
)

__all__ = [
    "Order",
    "OrderSideEnum",
    "OrderStatusEnum",
    "OrderTypeEnum",
    "Position",
    "TimeInForceEnum",
    "Trade",
]
