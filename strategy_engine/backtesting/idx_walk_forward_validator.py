"""Rolling window walk-forward validation for IDX strategies.

Implements anchored and rolling walk-forward analysis to test strategy
robustness across multiple out-of-sample periods.  Avoids look-ahead
bias by strictly separating in-sample (IS) and out-of-sample (OOS)
windows.

Usage::

    validator = IDXWalkForwardValidator(engine=backtest_engine)
    results = await validator.validate(strategy, market_data)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import TYPE_CHECKING

import pandas as pd

from shared.structured_json_logger import get_logger
from strategy_engine.backtesting.backtest_performance_metrics import (
    BacktestPerformanceMetrics,
)

if TYPE_CHECKING:
    from strategy_engine.backtesting.idx_vectorbt_backtest_engine import (
        BacktestResult,
        IDXVectorbtBacktestEngine,
    )
    from strategy_engine.base_strategy_interface import BaseStrategyInterface

logger = get_logger(__name__)


@dataclass
class WalkForwardFold:
    """Result of a single walk-forward fold.

    Attributes:
        fold_index: Zero-based fold number.
        is_start: In-sample start date.
        is_end: In-sample end date.
        oos_start: Out-of-sample start date.
        oos_end: Out-of-sample end date.
        oos_result: Backtest result for the OOS period.
        oos_metrics: Performance metrics for the OOS period.
    """

    fold_index: int
    is_start: datetime
    is_end: datetime
    oos_start: datetime
    oos_end: datetime
    oos_result: BacktestResult
    oos_metrics: dict[str, float] = field(default_factory=dict)
    is_metrics: dict[str, float] = field(default_factory=dict)
    is_oos_degradation: float = 0.0


@dataclass
class WalkForwardReport:
    """Aggregated walk-forward validation report.

    Attributes:
        strategy_id: Strategy identifier.
        folds: List of individual fold results.
        aggregate_metrics: Metrics aggregated across all OOS periods.
        oos_efficiency: Ratio of OOS Sharpe to IS Sharpe.
    """

    strategy_id: str
    folds: list[WalkForwardFold]
    aggregate_metrics: dict[str, float] = field(default_factory=dict)
    oos_efficiency: float = 0.0


class IDXWalkForwardValidator:
    """Rolling window walk-forward validator for strategy robustness testing.

    The validator splits the data into ``n_folds`` sequential windows,
    each with an in-sample training period and out-of-sample test period.

    Args:
        engine: Backtest engine instance.
        is_months: In-sample window length in months.
        oos_months: Out-of-sample window length in months.
        n_folds: Number of walk-forward folds.
        anchored: If True, IS window always starts from the same date.
    """

    def __init__(
        self,
        engine: IDXVectorbtBacktestEngine,
        is_months: int = 12,
        oos_months: int = 3,
        n_folds: int = 4,
        anchored: bool = False,
    ) -> None:
        self._engine = engine
        self._is_months = is_months
        self._oos_months = oos_months
        self._n_folds = n_folds
        self._anchored = anchored
        self._metrics = BacktestPerformanceMetrics()

        logger.info(
            "walk_forward_validator_initialised",
            is_months=is_months,
            oos_months=oos_months,
            n_folds=n_folds,
            anchored=anchored,
        )

    async def validate(
        self,
        strategy: BaseStrategyInterface,
        market_data: pd.DataFrame,
        data_start: datetime,
    ) -> WalkForwardReport:
        """Run walk-forward validation across all folds.

        Args:
            strategy: Strategy instance to validate.
            market_data: Full historical data (multi-index DataFrame).
            data_start: Earliest available data date.

        Returns:
            WalkForwardReport with per-fold and aggregate results.
        """
        params = strategy.get_parameters()
        logger.info("walk_forward_start", strategy=params.name, n_folds=self._n_folds)

        folds: list[WalkForwardFold] = []
        all_oos_returns: list[pd.Series] = []

        for i in range(self._n_folds):
            is_start = data_start if self._anchored else data_start + timedelta(days=i * self._oos_months * 30)
            is_end = is_start + timedelta(days=self._is_months * 30)
            oos_start = is_end + timedelta(days=1)
            oos_end = oos_start + timedelta(days=self._oos_months * 30)

            # Run backtest on the in-sample window for performance comparison
            is_result = await self._engine.run(strategy, market_data, is_start, is_end)
            is_metrics = self._metrics.compute_all(is_result.returns)

            oos_result = await self._engine.run(strategy, market_data, oos_start, oos_end)
            oos_metrics = self._metrics.compute_all(oos_result.returns)

            # Compute IS/OOS performance degradation ratio (OOS Sharpe / IS Sharpe)
            is_sharpe = is_metrics.get("sharpe_ratio", 0.0)
            oos_sharpe = oos_metrics.get("sharpe_ratio", 0.0)
            degradation = oos_sharpe / is_sharpe if is_sharpe != 0.0 else 0.0

            fold = WalkForwardFold(
                fold_index=i,
                is_start=is_start,
                is_end=is_end,
                oos_start=oos_start,
                oos_end=oos_end,
                oos_result=oos_result,
                oos_metrics=oos_metrics,
                is_metrics=is_metrics,
                is_oos_degradation=round(degradation, 4),
            )
            folds.append(fold)
            all_oos_returns.append(oos_result.returns)

            logger.info(
                "walk_forward_fold_complete",
                fold=i,
                oos_sharpe=oos_metrics.get("sharpe_ratio", 0.0),
            )

        # Aggregate OOS metrics.
        combined_returns = pd.concat(all_oos_returns)
        aggregate = self._metrics.compute_all(combined_returns)

        report = WalkForwardReport(
            strategy_id=params.name,
            folds=folds,
            aggregate_metrics=aggregate,
            oos_efficiency=aggregate.get("sharpe_ratio", 0.0),
        )

        logger.info(
            "walk_forward_complete",
            aggregate_sharpe=aggregate.get("sharpe_ratio", 0.0),
            n_folds=len(folds),
        )
        return report
