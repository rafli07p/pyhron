"""Factor Lab for the Pyhron Research Platform.

Interactive factor research environment for creating, testing,
comparing, and backtesting quantitative factors. Supports cross-sectional
and time-series factor analysis with IC, turnover, and return
attribution.
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
class FactorDefinition:
    """Definition of a quantitative factor."""

    factor_id: UUID = field(default_factory=uuid4)
    name: str = ""
    description: str = ""
    expression: str = ""  # Factor computation expression or function reference
    universe: str = "all"  # Symbol universe (e.g., "SP500", "IDX30")
    frequency: str = "daily"  # Rebalance frequency
    lookback_days: int = 252
    created_at: datetime = field(default_factory=lambda: datetime.now(tz=UTC))
    tags: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Serialize factor definition to a dictionary."""
        return {
            "factor_id": str(self.factor_id),
            "name": self.name,
            "description": self.description,
            "expression": self.expression,
            "universe": self.universe,
            "frequency": self.frequency,
            "lookback_days": self.lookback_days,
            "created_at": self.created_at.isoformat(),
            "tags": self.tags,
        }


@dataclass
class FactorTestResult:
    """Results from testing a factor."""

    factor_name: str = ""
    ic_mean: float = 0.0
    ic_std: float = 0.0
    ic_ir: float = 0.0  # Information ratio: IC_mean / IC_std
    turnover_mean: float = 0.0
    quintile_returns: dict[str, float] = field(default_factory=dict)
    long_short_return: float = 0.0
    max_drawdown: float = 0.0
    hit_rate: float = 0.0
    num_periods: int = 0
    start_date: str | None = None
    end_date: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """Serialize test results to a dictionary."""
        return {
            "factor_name": self.factor_name,
            "ic_mean": self.ic_mean,
            "ic_std": self.ic_std,
            "ic_ir": self.ic_ir,
            "turnover_mean": self.turnover_mean,
            "quintile_returns": self.quintile_returns,
            "long_short_return": self.long_short_return,
            "max_drawdown": self.max_drawdown,
            "hit_rate": self.hit_rate,
            "num_periods": self.num_periods,
            "start_date": self.start_date,
            "end_date": self.end_date,
        }


class FactorLab:
    """Interactive factor research environment.

    Provides tools for creating quantitative factors, testing their
    predictive power, comparing multiple factors, and running factor-based
    backtests. Supports standard alpha factor analytics including
    information coefficient (IC), turnover analysis, and quintile return
    spreads.
    """

    def __init__(self) -> None:
        self._factors: dict[str, FactorDefinition] = {}
        self._test_results: dict[str, FactorTestResult] = {}
        logger.info("FactorLab initialized")

    def create_factor(
        self,
        name: str,
        expression: str,
        description: str = "",
        universe: str = "all",
        frequency: str = "daily",
        lookback_days: int = 252,
        tags: list[str] | None = None,
    ) -> FactorDefinition:
        """Create a new factor definition.

        Parameters
        ----------
        name:
            Factor name (e.g., ``momentum_12m``, ``value_ep``).
        expression:
            Factor computation expression or callable reference.
            Examples: ``"returns(close, 252)"``, ``"rank(earnings/price)"``.
        description:
            Human-readable description.
        universe:
            Symbol universe to apply the factor to.
        frequency:
            Rebalance frequency (``daily``, ``weekly``, ``monthly``).
        lookback_days:
            Historical lookback period in trading days.
        tags:
            Tags for categorization.

        Returns
        -------
        FactorDefinition
            The created factor definition.
        """
        factor = FactorDefinition(
            name=name,
            expression=expression,
            description=description,
            universe=universe,
            frequency=frequency,
            lookback_days=lookback_days,
            tags=tags or [],
        )
        self._factors[name] = factor
        logger.info("Created factor '%s': %s", name, expression)
        return factor

    def test_factor(
        self,
        name: str,
        factor_values: pd.DataFrame,
        forward_returns: pd.DataFrame,
        quantiles: int = 5,
    ) -> FactorTestResult:
        """Test a factor's predictive power against forward returns.

        Parameters
        ----------
        name:
            Factor name to test (must exist in the registry).
        factor_values:
            DataFrame with DatetimeIndex rows and symbol columns,
            containing factor scores.
        forward_returns:
            DataFrame with same shape as ``factor_values`` containing
            forward returns for evaluation.
        quantiles:
            Number of quantile buckets for portfolio analysis.

        Returns
        -------
        FactorTestResult
            Comprehensive test results including IC, turnover, and
            quintile returns.

        Raises
        ------
        KeyError
            If the factor name is not found.
        """
        if name not in self._factors:
            raise KeyError(f"Factor not found: {name}")

        # Compute Information Coefficient (rank correlation per period)
        ic_series: list[float] = []
        for dt in factor_values.index:
            if dt not in forward_returns.index:
                continue
            fv = factor_values.loc[dt].dropna()
            fr = forward_returns.loc[dt].dropna()
            common = fv.index.intersection(fr.index)
            if len(common) < 10:
                continue
            rank_corr = fv[common].rank().corr(fr[common].rank())
            if not np.isnan(rank_corr):
                ic_series.append(float(rank_corr))

        ic_mean = float(np.mean(ic_series)) if ic_series else 0.0
        ic_std = float(np.std(ic_series)) if ic_series else 0.0
        ic_ir = ic_mean / ic_std if ic_std > 0 else 0.0

        # Compute turnover
        turnover_values: list[float] = []
        prev_ranks: pd.Series | None = None
        for dt in factor_values.index:
            current = factor_values.loc[dt].dropna().rank(pct=True)
            if prev_ranks is not None:
                common = current.index.intersection(prev_ranks.index)
                if len(common) > 0:
                    turnover = float((current[common] - prev_ranks[common]).abs().mean())
                    turnover_values.append(turnover)
            prev_ranks = current
        turnover_mean = float(np.mean(turnover_values)) if turnover_values else 0.0

        # Compute quintile returns
        quintile_rets: dict[str, float] = {}
        for q in range(1, quantiles + 1):
            q_returns: list[float] = []
            for dt in factor_values.index:
                if dt not in forward_returns.index:
                    continue
                fv = factor_values.loc[dt].dropna()
                fr = forward_returns.loc[dt].dropna()
                common = fv.index.intersection(fr.index)
                if len(common) < quantiles:
                    continue
                quantile_labels = pd.qcut(fv[common], quantiles, labels=False, duplicates="drop")
                mask = quantile_labels == (q - 1)
                if mask.any():
                    q_returns.append(float(fr[common][mask].mean()))
            quintile_rets[f"Q{q}"] = float(np.mean(q_returns)) if q_returns else 0.0

        long_short = quintile_rets.get(f"Q{quantiles}", 0.0) - quintile_rets.get("Q1", 0.0)

        result = FactorTestResult(
            factor_name=name,
            ic_mean=ic_mean,
            ic_std=ic_std,
            ic_ir=ic_ir,
            turnover_mean=turnover_mean,
            quintile_returns=quintile_rets,
            long_short_return=long_short,
            hit_rate=float(np.mean([1.0 if ic > 0 else 0.0 for ic in ic_series])) if ic_series else 0.0,
            num_periods=len(ic_series),
            start_date=str(factor_values.index[0]) if len(factor_values) > 0 else None,
            end_date=str(factor_values.index[-1]) if len(factor_values) > 0 else None,
        )

        self._test_results[name] = result
        logger.info("Tested factor '%s': IC=%.4f, IR=%.4f, L/S=%.4f", name, ic_mean, ic_ir, long_short)
        return result

    def compare_factors(self, factor_names: list[str]) -> list[dict[str, Any]]:
        """Compare test results across multiple factors.

        Parameters
        ----------
        factor_names:
            List of factor names to compare. Each must have been
            previously tested.

        Returns
        -------
        list[dict[str, Any]]
            Comparative summary sorted by IC Information Ratio.

        Raises
        ------
        KeyError
            If any factor has not been tested.
        """
        results: list[FactorTestResult] = []
        for name in factor_names:
            if name not in self._test_results:
                raise KeyError(f"Factor '{name}' has not been tested yet")
            results.append(self._test_results[name])

        results.sort(key=lambda r: r.ic_ir, reverse=True)
        logger.info("Compared %d factors; best IC IR: %s", len(results), results[0].factor_name if results else "N/A")
        return [r.to_dict() for r in results]

    def backtest_factor(
        self,
        name: str,
        prices: pd.DataFrame,
        factor_values: pd.DataFrame,
        top_n: int = 20,
        rebalance_frequency: str = "monthly",
        initial_capital: float = 1_000_000.0,
    ) -> dict[str, Any]:
        """Run a simple long-only factor backtest.

        Constructs an equal-weight portfolio of the top N stocks ranked
        by factor value and computes portfolio returns.

        Parameters
        ----------
        name:
            Factor name.
        prices:
            Price DataFrame (DatetimeIndex x symbols).
        factor_values:
            Factor score DataFrame (same shape as ``prices``).
        top_n:
            Number of top-ranked stocks to hold.
        rebalance_frequency:
            Rebalancing frequency (``daily``, ``weekly``, ``monthly``).
        initial_capital:
            Starting portfolio value.

        Returns
        -------
        dict[str, Any]
            Backtest results including total return, Sharpe ratio,
            and equity curve.
        """
        returns = prices.pct_change().dropna(how="all")
        portfolio_returns: list[float] = []
        rebalance_dates = self._get_rebalance_dates(factor_values.index, rebalance_frequency)

        current_holdings: pd.Index | None = None
        for dt in returns.index:
            if dt in rebalance_dates or current_holdings is None:
                fv = factor_values.loc[dt].dropna() if dt in factor_values.index else pd.Series(dtype=float)
                if len(fv) >= top_n:
                    current_holdings = fv.nlargest(top_n).index

            if current_holdings is not None and len(current_holdings) > 0:
                valid = current_holdings.intersection(returns.columns)
                if len(valid) > 0:
                    port_ret = float(returns.loc[dt, valid].mean())
                    portfolio_returns.append(port_ret)
                else:
                    portfolio_returns.append(0.0)
            else:
                portfolio_returns.append(0.0)

        portfolio_returns_arr = np.array(portfolio_returns)
        equity_curve = initial_capital * np.cumprod(1 + portfolio_returns_arr)

        total_return = float(equity_curve[-1] / initial_capital - 1) if len(equity_curve) > 0 else 0.0
        sharpe = float(np.mean(portfolio_returns_arr) / np.std(portfolio_returns_arr) * np.sqrt(252)) if np.std(portfolio_returns_arr) > 0 else 0.0

        running_max = np.maximum.accumulate(equity_curve) if len(equity_curve) > 0 else np.array([initial_capital])
        drawdown = (equity_curve - running_max) / running_max if len(running_max) > 0 else np.array([0.0])
        max_drawdown = float(np.min(drawdown))

        result = {
            "factor_name": name,
            "total_return": total_return,
            "sharpe_ratio": sharpe,
            "max_drawdown": max_drawdown,
            "num_periods": len(portfolio_returns),
            "initial_capital": initial_capital,
            "final_value": float(equity_curve[-1]) if len(equity_curve) > 0 else initial_capital,
            "top_n": top_n,
            "rebalance_frequency": rebalance_frequency,
        }

        logger.info(
            "Factor backtest '%s': return=%.2f%%, Sharpe=%.2f, MaxDD=%.2f%%",
            name, total_return * 100, sharpe, max_drawdown * 100,
        )
        return result

    @staticmethod
    def _get_rebalance_dates(index: pd.DatetimeIndex, frequency: str) -> set[Any]:
        """Get rebalance dates from an index based on frequency."""
        if frequency == "daily":
            return set(index)
        if frequency == "weekly":
            return {dt for dt in index if dt.weekday() == 0}  # Mondays
        if frequency == "monthly":
            dates = set()
            seen_months: set[tuple[int, int]] = set()
            for dt in index:
                key = (dt.year, dt.month)
                if key not in seen_months:
                    seen_months.add(key)
                    dates.add(dt)
            return dates
        return set(index)


__all__ = [
    "FactorDefinition",
    "FactorLab",
    "FactorTestResult",
]
