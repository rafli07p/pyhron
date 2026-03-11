"""Parameter sensitivity analysis for momentum strategy.

Performs systematic grid search across formation_months, skip_months,
top_pct, and max_sector_concentration to identify robust parameter
regions vs sharp optima (which indicate overfitting).

Usage::

    results = run_parameter_sensitivity(prices, volumes, trading_values,
                                        instrument_metadata, capital, cost_model)
"""

from __future__ import annotations

import itertools
from typing import TYPE_CHECKING, Any

import pandas as pd

from shared.structured_json_logger import get_logger

if TYPE_CHECKING:
    from datetime import date
    from decimal import Decimal

    from strategy_engine.backtesting.idx_transaction_cost_model import (
        IDXTransactionCostModel,
    )

logger = get_logger(__name__)


def run_parameter_sensitivity(
    prices: pd.DataFrame,
    volumes: pd.DataFrame,
    trading_values: pd.DataFrame,
    instrument_metadata: pd.DataFrame,
    initial_capital_idr: Decimal,
    cost_model: IDXTransactionCostModel,
    start_date: date | None = None,
    end_date: date | None = None,
) -> pd.DataFrame:
    """Systematic sensitivity analysis across parameter grid.

    Parameter grid:
      formation_months: [3, 6, 9, 12]
      skip_months: [0, 1]
      top_pct: [0.10, 0.20, 0.30]
      max_sector_concentration: [0.30, 0.40, 0.50]

    Returns DataFrame with one row per parameter combination including
    Sharpe, CAGR, MaxDD, Calmar for each.

    Parameters
    ----------
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
    cost_model:
        IDX transaction cost model.
    start_date:
        Backtest start date (defaults to first date in prices).
    end_date:
        Backtest end date (defaults to last date in prices).
    """
    from strategy_engine.backtesting.idx_vectorbt_backtest_engine import (
        run_momentum_backtest,
    )
    from strategy_engine.idx_momentum_cross_section_strategy import (
        IDXMomentumCrossSectionStrategy,
    )

    if start_date is None:
        start_date = prices.index[0].date() if hasattr(prices.index[0], "date") else prices.index[0]
    if end_date is None:
        end_date = prices.index[-1].date() if hasattr(prices.index[-1], "date") else prices.index[-1]

    param_grid: dict[str, list[Any]] = {
        "formation_months": [3, 6, 9, 12],
        "skip_months": [0, 1],
        "top_pct": [0.10, 0.20, 0.30],
        "max_sector_concentration": [0.30, 0.40, 0.50],
    }

    keys = list(param_grid.keys())
    value_lists = list(param_grid.values())
    combos: list[tuple[Any, ...]] = list(itertools.product(*value_lists))

    results: list[dict[str, Any]] = []

    for combo in combos:
        params = dict(zip(keys, combo, strict=False))
        logger.info("sensitivity_run", **params)

        strategy = IDXMomentumCrossSectionStrategy(**params)
        result = run_momentum_backtest(
            strategy=strategy,
            prices=prices,
            volumes=volumes,
            trading_values=trading_values,
            instrument_metadata=instrument_metadata,
            initial_capital_idr=initial_capital_idr,
            start_date=start_date,
            end_date=end_date,
            cost_model=cost_model,
        )

        row = {
            **params,
            "sharpe_ratio": result.sharpe_ratio,
            "cagr_pct": result.cagr_pct,
            "max_drawdown_pct": result.max_drawdown_pct,
            "calmar_ratio": result.calmar_ratio,
            "total_return_pct": result.total_return_pct,
            "total_trades": result.total_trades,
        }
        results.append(row)

    df = pd.DataFrame(results)
    logger.info(
        "sensitivity_complete",
        n_combinations=len(df),
        best_sharpe=float(df["sharpe_ratio"].max()) if not df.empty else 0.0,
    )
    return df
