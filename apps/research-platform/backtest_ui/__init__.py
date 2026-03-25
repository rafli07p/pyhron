"""Backtest UI for the Pyhron Research Platform.

Visual backtest configuration, execution, and results comparison.
Provides a high-level interface for defining backtest parameters,
running backtests through the research service, and analyzing results.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any, Optional
from uuid import UUID, uuid4

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


@dataclass
class BacktestConfig:
    """Configuration for a backtest run."""

    config_id: UUID = field(default_factory=uuid4)
    strategy_name: str = ""
    start_date: str = ""
    end_date: str = ""
    symbols: list[str] = field(default_factory=list)
    initial_capital: float = 1_000_000.0
    commission_bps: float = 5.0  # Basis points per trade
    slippage_bps: float = 2.0
    rebalance_frequency: str = "daily"
    benchmark: str = "SPY"
    parameters: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Serialize config to a dictionary."""
        return {
            "config_id": str(self.config_id),
            "strategy_name": self.strategy_name,
            "start_date": self.start_date,
            "end_date": self.end_date,
            "symbols": self.symbols,
            "initial_capital": self.initial_capital,
            "commission_bps": self.commission_bps,
            "slippage_bps": self.slippage_bps,
            "rebalance_frequency": self.rebalance_frequency,
            "benchmark": self.benchmark,
            "parameters": self.parameters,
        }


@dataclass
class BacktestResults:
    """Results from a completed backtest run."""

    backtest_id: UUID = field(default_factory=uuid4)
    config: BacktestConfig | None = None
    total_return: float = 0.0
    annualized_return: float = 0.0
    sharpe_ratio: float = 0.0
    sortino_ratio: float = 0.0
    max_drawdown: float = 0.0
    max_drawdown_duration_days: int = 0
    win_rate: float = 0.0
    profit_factor: float = 0.0
    total_trades: int = 0
    avg_trade_return: float = 0.0
    volatility: float = 0.0
    calmar_ratio: float = 0.0
    benchmark_return: float = 0.0
    alpha: float = 0.0
    beta: float = 0.0
    equity_curve: list[float] = field(default_factory=list)
    drawdown_series: list[float] = field(default_factory=list)
    monthly_returns: dict[str, float] = field(default_factory=dict)
    status: str = "completed"
    completed_at: datetime | None = None

    def to_dict(self) -> dict[str, Any]:
        """Serialize results to a dictionary."""
        return {
            "backtest_id": str(self.backtest_id),
            "strategy_name": self.config.strategy_name if self.config else "",
            "total_return": self.total_return,
            "annualized_return": self.annualized_return,
            "sharpe_ratio": self.sharpe_ratio,
            "sortino_ratio": self.sortino_ratio,
            "max_drawdown": self.max_drawdown,
            "max_drawdown_duration_days": self.max_drawdown_duration_days,
            "win_rate": self.win_rate,
            "profit_factor": self.profit_factor,
            "total_trades": self.total_trades,
            "volatility": self.volatility,
            "calmar_ratio": self.calmar_ratio,
            "benchmark_return": self.benchmark_return,
            "alpha": self.alpha,
            "beta": self.beta,
            "status": self.status,
        }


class BacktestUI:
    """Visual backtest configuration and results analysis.

    Provides a UI-oriented workflow for configuring backtests, executing
    them, reviewing results with performance metrics, and comparing
    multiple strategies side-by-side.
    """

    def __init__(self) -> None:
        self._configs: dict[str, BacktestConfig] = {}
        self._results: dict[str, BacktestResults] = {}
        logger.info("BacktestUI initialized")

    def configure_backtest(
        self,
        strategy_name: str,
        start_date: str,
        end_date: str,
        symbols: list[str],
        initial_capital: float = 1_000_000.0,
        commission_bps: float = 5.0,
        slippage_bps: float = 2.0,
        rebalance_frequency: str = "daily",
        benchmark: str = "SPY",
        **parameters: Any,
    ) -> BacktestConfig:
        """Configure a backtest run.

        Parameters
        ----------
        strategy_name:
            Name of the strategy to backtest.
        start_date:
            Backtest start date (ISO format, e.g., ``2020-01-01``).
        end_date:
            Backtest end date (ISO format).
        symbols:
            Universe of symbols to trade.
        initial_capital:
            Starting portfolio value.
        commission_bps:
            Commission cost in basis points per trade.
        slippage_bps:
            Slippage estimate in basis points per trade.
        rebalance_frequency:
            Rebalancing frequency (``daily``, ``weekly``, ``monthly``).
        benchmark:
            Benchmark symbol for comparison.
        **parameters:
            Additional strategy-specific parameters.

        Returns
        -------
        BacktestConfig
            The created backtest configuration.
        """
        config = BacktestConfig(
            strategy_name=strategy_name,
            start_date=start_date,
            end_date=end_date,
            symbols=symbols,
            initial_capital=initial_capital,
            commission_bps=commission_bps,
            slippage_bps=slippage_bps,
            rebalance_frequency=rebalance_frequency,
            benchmark=benchmark,
            parameters=parameters,
        )
        self._configs[strategy_name] = config
        logger.info("Configured backtest '%s' (%s to %s, %d symbols)", strategy_name, start_date, end_date, len(symbols))
        return config

    def run_backtest(
        self,
        strategy_name: str,
        price_data: pd.DataFrame,
        signal_func: Any | None = None,
    ) -> BacktestResults:
        """Execute a configured backtest.

        Parameters
        ----------
        strategy_name:
            Name of a previously configured backtest.
        price_data:
            Price DataFrame (DatetimeIndex x symbols) with close prices.
        signal_func:
            Optional callable that takes a DataFrame and returns a
            signal DataFrame (-1, 0, 1 for short/flat/long). If
            ``None``, uses a simple momentum signal.

        Returns
        -------
        BacktestResults
            Comprehensive backtest results.

        Raises
        ------
        KeyError
            If the strategy has not been configured.
        """
        if strategy_name not in self._configs:
            raise KeyError(f"Strategy not configured: {strategy_name}")

        config = self._configs[strategy_name]
        returns = price_data.pct_change().dropna(how="all")

        # Generate signals
        if signal_func is not None:
            signals = signal_func(price_data)
        else:
            # Default momentum signal: long if price > SMA(20)
            sma = price_data.rolling(20).mean()
            signals = (price_data > sma).astype(float)

        # Compute portfolio returns with costs
        cost_per_trade = (config.commission_bps + config.slippage_bps) / 10_000
        signal_changes = signals.diff().abs().fillna(0)
        trade_costs = signal_changes * cost_per_trade

        portfolio_returns = (signals.shift(1) * returns - trade_costs).mean(axis=1).dropna()
        total_trades = int(signal_changes.sum().sum())

        # Compute equity curve
        equity = config.initial_capital * (1 + portfolio_returns).cumprod()
        equity_list = equity.tolist()

        # Performance metrics
        total_return = float(equity.iloc[-1] / config.initial_capital - 1) if len(equity) > 0 else 0.0
        n_years = len(portfolio_returns) / 252.0
        annualized_return = float((1 + total_return) ** (1 / n_years) - 1) if n_years > 0 else 0.0
        volatility = float(portfolio_returns.std() * np.sqrt(252))
        sharpe = float(annualized_return / volatility) if volatility > 0 else 0.0

        # Sortino (downside deviation)
        downside = portfolio_returns[portfolio_returns < 0]
        downside_std = float(downside.std() * np.sqrt(252)) if len(downside) > 0 else 0.0
        sortino = float(annualized_return / downside_std) if downside_std > 0 else 0.0

        # Drawdown
        running_max = equity.cummax()
        drawdown_series = (equity - running_max) / running_max
        max_drawdown = float(drawdown_series.min())

        # Win rate
        winning = portfolio_returns[portfolio_returns > 0]
        losing = portfolio_returns[portfolio_returns < 0]
        win_rate = float(len(winning) / len(portfolio_returns)) if len(portfolio_returns) > 0 else 0.0

        gross_profit = float(winning.sum()) if len(winning) > 0 else 0.0
        gross_loss = float(abs(losing.sum())) if len(losing) > 0 else 0.0
        profit_factor = gross_profit / gross_loss if gross_loss > 0 else float("inf")

        calmar = float(annualized_return / abs(max_drawdown)) if max_drawdown != 0 else 0.0

        results = BacktestResults(
            config=config,
            total_return=total_return,
            annualized_return=annualized_return,
            sharpe_ratio=sharpe,
            sortino_ratio=sortino,
            max_drawdown=max_drawdown,
            win_rate=win_rate,
            profit_factor=profit_factor,
            total_trades=total_trades,
            avg_trade_return=float(portfolio_returns.mean()),
            volatility=volatility,
            calmar_ratio=calmar,
            equity_curve=equity_list,
            drawdown_series=drawdown_series.tolist(),
            status="completed",
            completed_at=datetime.now(tz=UTC),
        )

        self._results[strategy_name] = results
        logger.info(
            "Backtest '%s' completed: return=%.2f%%, Sharpe=%.2f, MaxDD=%.2f%%",
            strategy_name, total_return * 100, sharpe, max_drawdown * 100,
        )
        return results

    def show_results(self, strategy_name: str) -> dict[str, Any]:
        """Show detailed results for a completed backtest.

        Parameters
        ----------
        strategy_name:
            Name of the strategy whose results to display.

        Returns
        -------
        dict[str, Any]
            Full results dictionary.

        Raises
        ------
        KeyError
            If no results exist for the strategy.
        """
        if strategy_name not in self._results:
            raise KeyError(f"No results for strategy: {strategy_name}")
        return self._results[strategy_name].to_dict()

    def compare_strategies(self, strategy_names: list[str]) -> list[dict[str, Any]]:
        """Compare results across multiple backtested strategies.

        Parameters
        ----------
        strategy_names:
            List of strategy names to compare.

        Returns
        -------
        list[dict[str, Any]]
            Comparative summary sorted by Sharpe ratio descending.

        Raises
        ------
        KeyError
            If any strategy has not been backtested.
        """
        comparison: list[dict[str, Any]] = []
        for name in strategy_names:
            if name not in self._results:
                raise KeyError(f"No results for strategy: {name}")
            comparison.append(self._results[name].to_dict())

        comparison.sort(key=lambda r: r.get("sharpe_ratio", 0), reverse=True)
        logger.info(
            "Compared %d strategies; best Sharpe: %s",
            len(comparison),
            comparison[0].get("strategy_name") if comparison else "N/A",
        )
        return comparison


__all__ = [
    "BacktestConfig",
    "BacktestResults",
    "BacktestUI",
]
