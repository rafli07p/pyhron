"""Vectorbt wrapper for IDX strategy backtesting.

Provides a high-level interface around vectorbt for running vectorised
backtests of Pyhron strategies, including IDX-specific transaction costs,
lot-size constraints, and T+2 settlement handling.

Usage::

    engine = IDXVectorbtBacktestEngine(cost_model=cost_model)
    result = await engine.run(strategy, market_data, start, end)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

import pandas as pd
import vectorbt as vbt

from shared.structured_json_logger import get_logger
from strategy_engine.backtesting.idx_transaction_cost_model import IDXTransactionCostModel

if TYPE_CHECKING:
    from datetime import datetime

    from strategy_engine.base_strategy_interface import BaseStrategyInterface

logger = get_logger(__name__)


@dataclass
class BacktestResult:
    """Container for backtest output.

    Attributes:
        strategy_id: Identifier of the backtested strategy.
        start_date: Backtest start date.
        end_date: Backtest end date.
        portfolio_value: Time series of portfolio NAV.
        returns: Daily returns series.
        trades: DataFrame of executed trades.
        metrics: Dictionary of performance metrics.
    """

    strategy_id: str
    start_date: datetime
    end_date: datetime
    portfolio_value: pd.Series
    returns: pd.Series
    trades: pd.DataFrame
    metrics: dict[str, float] = field(default_factory=dict)


class IDXVectorbtBacktestEngine:
    """Vectorbt-based backtest engine with IDX market microstructure.

    Handles lot-size rounding (100 shares), asymmetric transaction costs
    (0.15% buy / 0.25% sell including tax), and T+2 settlement delay.

    Args:
        cost_model: IDX transaction cost model instance.
        initial_capital: Starting capital in IDR (default 1 billion).
        lot_size: IDX lot size (default 100 shares).
    """

    def __init__(
        self,
        cost_model: IDXTransactionCostModel | None = None,
        initial_capital: float = 1_000_000_000.0,
        lot_size: int = 100,
    ) -> None:
        self._cost_model = cost_model or IDXTransactionCostModel()
        self._initial_capital = initial_capital
        self._lot_size = lot_size

        logger.info(
            "backtest_engine_initialised",
            initial_capital=self._initial_capital,
            lot_size=self._lot_size,
        )

    async def run(
        self,
        strategy: BaseStrategyInterface,
        market_data: pd.DataFrame,
        start_date: datetime,
        end_date: datetime,
    ) -> BacktestResult:
        """Execute a full backtest for the given strategy.

        Args:
            strategy: Strategy instance implementing BaseStrategyInterface.
            market_data: Multi-index (date, symbol) OHLCV DataFrame.
            start_date: Backtest start date.
            end_date: Backtest end date.

        Returns:
            BacktestResult with portfolio value, returns, trades, and metrics.
        """
        params = strategy.get_parameters()
        logger.info(
            "backtest_run_start",
            strategy=params.name,
            start=start_date.isoformat(),
            end=end_date.isoformat(),
        )

        if isinstance(market_data.index, pd.MultiIndex):
            close = market_data["close"].unstack(level="symbol")
        else:
            close = market_data.pivot(columns="symbol", values="close")

        close = close.loc[(close.index >= start_date) & (close.index <= end_date)].sort_index()

        # Generate signals at each rebalance date.
        rebalance_dates = self._get_rebalance_dates(close.index, params.rebalance_frequency)

        target_weights = pd.DataFrame(0.0, index=close.index, columns=close.columns)

        for rdate in rebalance_dates:
            hist = market_data.loc[market_data.index.get_level_values(0) <= rdate]
            signals = await strategy.generate_signals(hist, rdate)
            for sig in signals:
                if sig.symbol in target_weights.columns:
                    target_weights.loc[rdate:, sig.symbol] = sig.target_weight

        # Apply lot-size rounding.
        shares = (target_weights * self._initial_capital) / close
        shares = (shares // self._lot_size) * self._lot_size
        shares = shares.fillna(0).astype(int)

        # Build portfolio using vectorbt.
        portfolio = vbt.Portfolio.from_orders(
            close=close,
            size=shares.diff().fillna(shares),
            size_type="amount",
            init_cash=self._initial_capital,
            fees=self._cost_model.effective_round_trip_cost(),
            freq="1D",
        )

        result = BacktestResult(
            strategy_id=params.name,
            start_date=start_date,
            end_date=end_date,
            portfolio_value=portfolio.value(),
            returns=portfolio.returns(),
            trades=portfolio.trades.records_readable,
        )

        logger.info(
            "backtest_run_complete",
            strategy=params.name,
            total_return=float(portfolio.total_return()),
        )
        return result

    @staticmethod
    def _get_rebalance_dates(date_index: pd.DatetimeIndex, frequency: str) -> list[datetime]:
        """Extract rebalance dates from date index based on frequency.

        Args:
            date_index: Available trading dates.
            frequency: One of ``daily``, ``weekly``, ``monthly``, ``quarterly``.

        Returns:
            List of rebalance dates.
        """
        if frequency == "daily":
            return list(date_index)
        if frequency == "weekly":
            return list(date_index[date_index.dayofweek == 4])
        if frequency == "monthly":
            grouped = pd.Series(date_index, index=date_index).groupby(date_index.to_period("M"))
            return [g.iloc[-1] for _, g in grouped]
        if frequency == "quarterly":
            grouped = pd.Series(date_index, index=date_index).groupby(date_index.to_period("Q"))
            return [g.iloc[-1] for _, g in grouped]
        return list(date_index)
