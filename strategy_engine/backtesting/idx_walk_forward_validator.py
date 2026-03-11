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

import itertools
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import TYPE_CHECKING

import pandas as pd

from shared.structured_json_logger import get_logger
from strategy_engine.backtesting.backtest_performance_metrics import (
    BacktestPerformanceMetrics,
)

if TYPE_CHECKING:
    from decimal import Decimal

    from strategy_engine.backtesting.idx_vectorbt_backtest_engine import (
        BacktestResult,
        IDXVectorbtBacktestEngine,
    )
    from strategy_engine.base_strategy_interface import BaseStrategyInterface

logger = get_logger(__name__)


@dataclass
class WalkForwardFold:
    """Result of a single walk-forward fold."""

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
    """Aggregated walk-forward validation report."""

    strategy_id: str
    folds: list[WalkForwardFold]
    aggregate_metrics: dict[str, float] = field(default_factory=dict)
    oos_efficiency: float = 0.0


@dataclass
class WalkForwardResult:
    """Enhanced walk-forward result with grid search and overfitting detection."""

    n_splits: int
    oos_sharpe: float
    oos_cagr: float
    oos_max_drawdown: float
    oos_calmar: float
    is_oos_sharpe_ratio: float
    best_params_per_fold: list[dict]
    param_stability_score: float
    fold_results: list[BacktestResult]
    equity_curve_oos: pd.Series = field(default_factory=lambda: pd.Series(dtype=float))


class IDXWalkForwardValidator:
    """Rolling window walk-forward validator for strategy robustness testing."""

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
        """Run walk-forward validation across all folds."""
        params = strategy.get_parameters()
        logger.info("walk_forward_start", strategy=params.name, n_folds=self._n_folds)

        folds: list[WalkForwardFold] = []
        all_oos_returns: list[pd.Series] = []

        for i in range(self._n_folds):
            is_start = data_start if self._anchored else data_start + timedelta(days=i * self._oos_months * 30)
            is_end = is_start + timedelta(days=self._is_months * 30)
            oos_start = is_end + timedelta(days=1)
            oos_end = oos_start + timedelta(days=self._oos_months * 30)

            is_result = await self._engine.run(strategy, market_data, is_start, is_end)
            is_metrics = self._metrics.compute_all(is_result.returns)

            oos_result = await self._engine.run(
                strategy,
                market_data,
                oos_start,
                oos_end,
            )
            oos_metrics = self._metrics.compute_all(oos_result.returns)

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


def run_walk_forward(
    strategy_class: type,
    prices: pd.DataFrame,
    volumes: pd.DataFrame,
    trading_values: pd.DataFrame,
    instrument_metadata: pd.DataFrame,
    initial_capital_idr: Decimal,
    param_grid: dict,
    n_splits: int = 5,
    train_pct: float = 0.70,
    cost_model: object | None = None,
    optimization_metric: str = "sharpe_ratio",
) -> WalkForwardResult:
    """Walk-forward optimization with grid search over parameter space.

    Parameters
    ----------
    strategy_class:
        Strategy class to instantiate with different parameters.
    prices:
        (dates, symbols) adjusted close.
    volumes:
        (dates, symbols) volume.
    trading_values:
        (dates, symbols) IDR value.
    instrument_metadata:
        Columns: symbol, sector, lot_size, is_active.
    initial_capital_idr:
        Starting capital.
    param_grid:
        e.g. {"formation_months": [6,9,12], "top_pct": [0.1,0.2,0.3]}
    n_splits:
        Number of expanding windows.
    train_pct:
        Fraction for in-sample per fold.
    cost_model:
        IDXTransactionCostModel instance.
    optimization_metric:
        Metric to maximize on IS period.
    """
    from strategy_engine.backtesting.idx_transaction_cost_model import (
        IDXTransactionCostModel,
    )
    from strategy_engine.backtesting.idx_vectorbt_backtest_engine import (
        run_momentum_backtest,
    )

    if cost_model is None:
        cost_model = IDXTransactionCostModel()

    all_dates = prices.index.sort_values()
    total_days = len(all_dates)

    # Generate all parameter combinations
    keys = list(param_grid.keys())
    values = list(param_grid.values())
    param_combos = [dict(zip(keys, combo, strict=False)) for combo in itertools.product(*values)]

    best_params_per_fold: list[dict] = []
    fold_results: list = []
    all_oos_curves: list[pd.Series] = []
    all_is_sharpes: list[float] = []
    all_oos_sharpes: list[float] = []

    for fold_idx in range(n_splits):
        # Anchored expanding window
        # Anchored expanding window
        window_size = total_days // n_splits
        is_end_idx = int(total_days * train_pct) + fold_idx * window_size // n_splits
        is_end_idx = min(is_end_idx, total_days - window_size)
        oos_start_idx = is_end_idx
        oos_end_idx = min(oos_start_idx + window_size, total_days - 1)

        if oos_start_idx >= oos_end_idx:
            continue

        is_end_date = all_dates[is_end_idx].date() if hasattr(all_dates[is_end_idx], "date") else all_dates[is_end_idx]
        is_start_date = all_dates[0].date() if hasattr(all_dates[0], "date") else all_dates[0]
        oos_start_date = (
            all_dates[oos_start_idx].date() if hasattr(all_dates[oos_start_idx], "date") else all_dates[oos_start_idx]
        )
        oos_end_date = (
            all_dates[oos_end_idx].date() if hasattr(all_dates[oos_end_idx], "date") else all_dates[oos_end_idx]
        )

        # Grid search on IS period
        best_metric = float("-inf")
        best_params = param_combos[0] if param_combos else {}

        for params in param_combos:
            strategy = strategy_class(**params)
            result = run_momentum_backtest(
                strategy=strategy,
                prices=prices,
                volumes=volumes,
                trading_values=trading_values,
                instrument_metadata=instrument_metadata,
                initial_capital_idr=initial_capital_idr,
                start_date=is_start_date,
                end_date=is_end_date,
                cost_model=cost_model,
            )
            metric_val = getattr(result, optimization_metric, 0.0)
            if metric_val > best_metric:
                best_metric = metric_val
                best_params = params

        best_params_per_fold.append(dict(best_params))
        all_is_sharpes.append(best_metric if optimization_metric == "sharpe_ratio" else 0.0)

        # Run OOS with best params
        strategy = strategy_class(**best_params)
        oos_result = run_momentum_backtest(
            strategy=strategy,
            prices=prices,
            volumes=volumes,
            trading_values=trading_values,
            instrument_metadata=instrument_metadata,
            initial_capital_idr=initial_capital_idr,
            start_date=oos_start_date,
            end_date=oos_end_date,
            cost_model=cost_model,
        )
        fold_results.append(oos_result)
        all_oos_sharpes.append(oos_result.sharpe_ratio)
        if not oos_result.equity_curve.empty:
            all_oos_curves.append(oos_result.equity_curve)

        logger.info(
            "walk_forward_fold_complete",
            fold=fold_idx,
            best_params=best_params,
            oos_sharpe=oos_result.sharpe_ratio,
        )

    # Aggregate
    avg_is_sharpe = sum(all_is_sharpes) / len(all_is_sharpes) if all_is_sharpes else 0.0
    avg_oos_sharpe = sum(all_oos_sharpes) / len(all_oos_sharpes) if all_oos_sharpes else 0.0
    is_oos_ratio = avg_is_sharpe / avg_oos_sharpe if avg_oos_sharpe != 0 else float("inf")

    # Param stability: fraction of folds selecting the same params
    if best_params_per_fold:
        param_strs = [str(sorted(p.items())) for p in best_params_per_fold]
        most_common = max(set(param_strs), key=param_strs.count)
        param_stability = param_strs.count(most_common) / len(param_strs)
    else:
        param_stability = 0.0

    # Overfitting warning
    if is_oos_ratio > 2.0 or param_stability < 0.4:
        logger.warning(
            "Walk-forward suggests potential overfitting. "
            "IS/OOS Sharpe ratio: %.2f (threshold: 2.0) "
            "Param stability: %.2f%% (threshold: 40%%)",
            is_oos_ratio,
            param_stability * 100,
        )

    # Concatenate OOS equity curves
    equity_oos = pd.concat(all_oos_curves) if all_oos_curves else pd.Series(dtype=float)

    avg_cagr = sum(r.cagr_pct for r in fold_results) / len(fold_results) if fold_results else 0.0
    avg_max_dd = sum(r.max_drawdown_pct for r in fold_results) / len(fold_results) if fold_results else 0.0
    avg_calmar = sum(r.calmar_ratio for r in fold_results) / len(fold_results) if fold_results else 0.0

    return WalkForwardResult(
        n_splits=n_splits,
        oos_sharpe=avg_oos_sharpe,
        oos_cagr=avg_cagr,
        oos_max_drawdown=avg_max_dd,
        oos_calmar=avg_calmar,
        is_oos_sharpe_ratio=is_oos_ratio,
        best_params_per_fold=best_params_per_fold,
        param_stability_score=param_stability,
        fold_results=fold_results,
        equity_curve_oos=equity_oos,
    )
