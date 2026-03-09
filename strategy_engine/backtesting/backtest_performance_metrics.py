"""Backtest performance metrics calculator.

Computes standard risk-adjusted performance metrics for strategy
evaluation: Sharpe ratio, Sortino ratio, Calmar ratio, maximum
drawdown, win rate, and related statistics.

Usage::

    metrics = BacktestPerformanceMetrics()
    result = metrics.compute_all(daily_returns)
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

import numpy as np

from shared.structured_json_logger import get_logger

if TYPE_CHECKING:
    import pandas as pd

logger = get_logger(__name__)

_TRADING_DAYS_PER_YEAR: int = 252
_RISK_FREE_RATE_ANNUAL: float = 0.065  # BI rate approximation


@dataclass(frozen=True)
class DrawdownInfo:
    """Maximum drawdown details.

    Attributes:
        max_drawdown: Maximum peak-to-trough decline as a fraction.
        peak_date: Date of the peak before the drawdown.
        trough_date: Date of the trough.
        recovery_date: Date of recovery (None if not recovered).
        duration_days: Number of calendar days in the drawdown.
    """

    max_drawdown: float
    peak_date: Any
    trough_date: Any
    recovery_date: Any
    duration_days: int


class BacktestPerformanceMetrics:
    """Calculator for standard backtest performance metrics.

    All ratios are annualised using 252 trading days unless otherwise
    specified.  Risk-free rate defaults to BI rate (~6.5%).

    Args:
        risk_free_rate: Annual risk-free rate (default 0.065).
        trading_days: Trading days per year (default 252).
    """

    def __init__(
        self,
        risk_free_rate: float = _RISK_FREE_RATE_ANNUAL,
        trading_days: int = _TRADING_DAYS_PER_YEAR,
    ) -> None:
        self._rf = risk_free_rate
        self._td = trading_days
        self._rf_daily = (1 + self._rf) ** (1 / self._td) - 1

    def sharpe_ratio(self, returns: pd.Series) -> float:
        """Annualised Sharpe ratio.

        Args:
            returns: Daily return series.

        Returns:
            Annualised Sharpe ratio.
        """
        excess = returns - self._rf_daily
        if excess.std() == 0:
            return 0.0
        return float(excess.mean() / excess.std() * np.sqrt(self._td))

    def sortino_ratio(self, returns: pd.Series) -> float:
        """Annualised Sortino ratio (downside deviation only).

        Args:
            returns: Daily return series.

        Returns:
            Annualised Sortino ratio.
        """
        excess = returns - self._rf_daily
        downside = excess[excess < 0]
        downside_std = downside.std() if len(downside) > 0 else 0.0
        if downside_std == 0:
            return 0.0
        return float(excess.mean() / downside_std * np.sqrt(self._td))

    def calmar_ratio(self, returns: pd.Series) -> float:
        """Calmar ratio (annualised return / max drawdown).

        Args:
            returns: Daily return series.

        Returns:
            Calmar ratio.
        """
        dd = self.max_drawdown(returns)
        if dd.max_drawdown == 0:
            return 0.0
        annual_return = float((1 + returns).prod() ** (self._td / len(returns)) - 1)
        return annual_return / abs(dd.max_drawdown)

    def max_drawdown(self, returns: pd.Series) -> DrawdownInfo:
        """Compute maximum drawdown with dates.

        Args:
            returns: Daily return series.

        Returns:
            DrawdownInfo with peak, trough, recovery dates, and magnitude.
        """
        cum = (1 + returns).cumprod()
        running_max = cum.cummax()
        drawdowns = cum / running_max - 1

        trough_idx = drawdowns.idxmin()
        max_dd = float(drawdowns.min())

        peak_idx = cum.loc[:trough_idx].idxmax()

        recovery_mask = cum.loc[trough_idx:] >= cum.loc[peak_idx]
        recovery_idx = recovery_mask[recovery_mask].index[0] if recovery_mask.any() else None

        duration = (trough_idx - peak_idx).days if hasattr(trough_idx, "days") else 0

        return DrawdownInfo(
            max_drawdown=max_dd,
            peak_date=peak_idx,
            trough_date=trough_idx,
            recovery_date=recovery_idx,
            duration_days=duration,
        )

    def win_rate(self, returns: pd.Series) -> float:
        """Fraction of positive-return days.

        Args:
            returns: Daily return series.

        Returns:
            Win rate as a fraction in [0, 1].
        """
        if len(returns) == 0:
            return 0.0
        return float((returns > 0).sum() / len(returns))

    def profit_factor(self, returns: pd.Series) -> float:
        """Ratio of gross profits to gross losses.

        Args:
            returns: Daily return series.

        Returns:
            Profit factor (> 1 is profitable).
        """
        gains = returns[returns > 0].sum()
        losses = abs(returns[returns < 0].sum())
        if losses == 0:
            return float("inf") if gains > 0 else 0.0
        return float(gains / losses)

    def compute_all(self, returns: pd.Series) -> dict[str, float]:
        """Compute all metrics and return as dictionary.

        Args:
            returns: Daily return series.

        Returns:
            Dictionary of metric name to value.
        """
        dd = self.max_drawdown(returns)
        annual_return = float((1 + returns).prod() ** (self._td / max(len(returns), 1)) - 1)

        result = {
            "annual_return": round(annual_return, 6),
            "sharpe_ratio": round(self.sharpe_ratio(returns), 4),
            "sortino_ratio": round(self.sortino_ratio(returns), 4),
            "calmar_ratio": round(self.calmar_ratio(returns), 4),
            "max_drawdown": round(dd.max_drawdown, 6),
            "win_rate": round(self.win_rate(returns), 4),
            "profit_factor": round(self.profit_factor(returns), 4),
            "volatility": round(float(returns.std() * np.sqrt(self._td)), 6),
            "total_return": round(float((1 + returns).prod() - 1), 6),
        }

        logger.info("performance_metrics_computed", **result)
        return result
