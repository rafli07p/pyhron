"""Backtesting sub-package for the Pyhron Strategy Engine.

Provides:

* :class:`IDXVectorBTBacktestEngine` — VectorBT wrapper with IDX cost model.
* :class:`IDXWalkForwardValidator` — Rolling train/test walk-forward analysis.
* :class:`IDXTransactionCostModel` — IDX-specific commission, tax, and lot sizing.
* :class:`BacktestPerformanceMetrics` — Sharpe, Sortino, Calmar, and more.
"""

from strategy_engine.backtesting.backtest_performance_metrics import (
    BacktestPerformanceMetrics,
)
from strategy_engine.backtesting.idx_transaction_cost_model import (
    IDXTransactionCostModel,
)

try:
    from strategy_engine.backtesting.idx_vectorbt_backtest_engine import (
        IDXVectorbtBacktestEngine,
    )
except ImportError:
    IDXVectorbtBacktestEngine = None  # type: ignore[assignment, misc]

try:
    from strategy_engine.backtesting.idx_walk_forward_validator import (
        IDXWalkForwardValidator,
    )
except ImportError:
    IDXWalkForwardValidator = None  # type: ignore[assignment, misc]

__all__ = [
    "BacktestPerformanceMetrics",
    "IDXTransactionCostModel",
    "IDXVectorbtBacktestEngine",
    "IDXWalkForwardValidator",
]
