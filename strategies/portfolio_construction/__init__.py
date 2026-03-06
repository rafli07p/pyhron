"""Enthropy Portfolio Construction.

Implements portfolio optimisation methods: mean-variance (Markowitz),
risk parity, equal weight, and maximum Sharpe ratio.  Supports
practical constraints like maximum position size, sector exposure
limits, and turnover limits.  Uses numpy and scipy.optimize for
numerical optimisation.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Optional

import numpy as np
import pandas as pd
import structlog
from scipy import optimize

logger = structlog.stdlib.get_logger(__name__)


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class PortfolioConstraints:
    """Constraints applied during portfolio optimisation."""

    max_position_size: float = 0.10  # max weight per asset
    min_position_size: float = 0.0   # min weight per asset (0 allows cash)
    max_sector_weight: float = 0.30  # max aggregate weight per sector
    max_turnover: float = 0.50       # max total turnover vs. current portfolio
    max_leverage: float = 1.0        # gross exposure limit
    long_only: bool = True           # disallow short positions


@dataclass(frozen=True)
class PortfolioAllocation:
    """Output of the portfolio optimiser."""

    weights: dict[str, float]            # symbol -> target weight
    expected_return: float = 0.0
    expected_volatility: float = 0.0
    sharpe_ratio: float = 0.0
    turnover: float = 0.0
    method: str = ""
    timestamp: datetime = field(default_factory=lambda: datetime.now(tz=timezone.utc))
    metadata: dict[str, Any] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Portfolio constructor
# ---------------------------------------------------------------------------

class PortfolioConstructor:
    """Optimise portfolio weights given signals, return forecasts, and constraints.

    Parameters
    ----------
    constraints:
        ``PortfolioConstraints`` governing the optimisation.
    risk_free_rate:
        Annualised risk-free rate for Sharpe calculations (default 0.05).
    sector_map:
        Optional mapping of symbol -> sector for sector constraints.
    """

    def __init__(
        self,
        constraints: Optional[PortfolioConstraints] = None,
        risk_free_rate: float = 0.05,
        sector_map: Optional[dict[str, str]] = None,
    ) -> None:
        self.constraints = constraints or PortfolioConstraints()
        self.risk_free_rate = risk_free_rate
        self.sector_map = sector_map or {}

    # -- public API ----------------------------------------------------------

    def optimize_portfolio(
        self,
        signals: dict[str, float],
        returns: pd.DataFrame,
        current_weights: Optional[dict[str, float]] = None,
    ) -> PortfolioAllocation:
        """Mean-variance optimisation (Markowitz).

        Maximises expected utility = mu'w - (lambda/2) w'Sigma w
        subject to constraints.

        Parameters
        ----------
        signals:
            Symbol -> expected return or alpha score.
        returns:
            DataFrame of historical returns (columns = symbols).
        current_weights:
            Current portfolio weights for turnover constraint.
        """
        symbols = sorted(signals.keys())
        n = len(symbols)
        if n == 0:
            return PortfolioAllocation(weights={}, method="mean_variance")

        mu = np.array([signals[s] for s in symbols])
        cov = returns[symbols].cov().values

        # Regularise covariance
        cov += np.eye(n) * 1e-6

        current_w = np.array([
            (current_weights or {}).get(s, 0.0) for s in symbols
        ])

        # Risk aversion parameter
        risk_aversion = 2.0

        def objective(w: np.ndarray) -> float:
            port_ret = mu @ w
            port_var = w @ cov @ w
            return -(port_ret - (risk_aversion / 2) * port_var)

        bounds = self._build_bounds(n)
        constraints_list = self._build_constraints(n, current_w)

        w0 = np.ones(n) / n
        result = optimize.minimize(
            objective,
            w0,
            method="SLSQP",
            bounds=bounds,
            constraints=constraints_list,
            options={"maxiter": 500, "ftol": 1e-10},
        )

        if not result.success:
            logger.warning("mv_optimization_failed", message=result.message)

        weights = dict(zip(symbols, result.x.tolist()))
        port_ret = float(mu @ result.x)
        port_vol = float(np.sqrt(result.x @ cov @ result.x))
        sharpe = (port_ret - self.risk_free_rate) / port_vol if port_vol > 1e-12 else 0.0
        turnover = float(np.sum(np.abs(result.x - current_w)))

        return PortfolioAllocation(
            weights=weights,
            expected_return=port_ret,
            expected_volatility=port_vol,
            sharpe_ratio=sharpe,
            turnover=turnover,
            method="mean_variance",
        )

    def risk_parity(
        self,
        returns: pd.DataFrame,
        symbols: Optional[list[str]] = None,
    ) -> PortfolioAllocation:
        """Risk parity allocation: equalise risk contribution per asset.

        Each asset contributes equally to the total portfolio variance.
        """
        syms = symbols or list(returns.columns)
        n = len(syms)
        if n == 0:
            return PortfolioAllocation(weights={}, method="risk_parity")

        cov = returns[syms].cov().values
        cov += np.eye(n) * 1e-6

        def risk_contribution_error(w: np.ndarray) -> float:
            port_var = w @ cov @ w
            marginal = cov @ w
            rc = w * marginal
            rc_pct = rc / (port_var + 1e-12)
            target = 1.0 / n
            return float(np.sum((rc_pct - target) ** 2))

        bounds = [(0.001, self.constraints.max_position_size) for _ in range(n)]
        cons = [{"type": "eq", "fun": lambda w: np.sum(w) - 1.0}]
        w0 = np.ones(n) / n

        result = optimize.minimize(
            risk_contribution_error,
            w0,
            method="SLSQP",
            bounds=bounds,
            constraints=cons,
            options={"maxiter": 500},
        )

        weights = dict(zip(syms, result.x.tolist()))
        port_vol = float(np.sqrt(result.x @ cov @ result.x))

        return PortfolioAllocation(
            weights=weights,
            expected_volatility=port_vol,
            method="risk_parity",
        )

    def equal_weight(self, symbols: list[str]) -> PortfolioAllocation:
        """Equal-weight allocation across all symbols."""
        n = len(symbols)
        if n == 0:
            return PortfolioAllocation(weights={}, method="equal_weight")

        w = 1.0 / n
        weights = {s: w for s in symbols}
        return PortfolioAllocation(weights=weights, method="equal_weight")

    def max_sharpe(
        self,
        signals: dict[str, float],
        returns: pd.DataFrame,
    ) -> PortfolioAllocation:
        """Maximum Sharpe ratio portfolio.

        Maximises (mu'w - rf) / sqrt(w'Sigma w) subject to constraints.
        """
        symbols = sorted(signals.keys())
        n = len(symbols)
        if n == 0:
            return PortfolioAllocation(weights={}, method="max_sharpe")

        mu = np.array([signals[s] for s in symbols])
        cov = returns[symbols].cov().values
        cov += np.eye(n) * 1e-6

        def neg_sharpe(w: np.ndarray) -> float:
            port_ret = mu @ w
            port_vol = np.sqrt(w @ cov @ w + 1e-12)
            return -(port_ret - self.risk_free_rate) / port_vol

        bounds = self._build_bounds(n)
        cons = [{"type": "eq", "fun": lambda w: np.sum(w) - 1.0}]
        w0 = np.ones(n) / n

        result = optimize.minimize(
            neg_sharpe,
            w0,
            method="SLSQP",
            bounds=bounds,
            constraints=cons,
            options={"maxiter": 500},
        )

        weights = dict(zip(symbols, result.x.tolist()))
        port_ret = float(mu @ result.x)
        port_vol = float(np.sqrt(result.x @ cov @ result.x))
        sharpe = (port_ret - self.risk_free_rate) / port_vol if port_vol > 1e-12 else 0.0

        return PortfolioAllocation(
            weights=weights,
            expected_return=port_ret,
            expected_volatility=port_vol,
            sharpe_ratio=sharpe,
            method="max_sharpe",
        )

    # -- constraint helpers --------------------------------------------------

    def _build_bounds(self, n: int) -> list[tuple[float, float]]:
        """Per-asset weight bounds respecting long_only and max_position_size."""
        lo = max(self.constraints.min_position_size, 0.0) if self.constraints.long_only else -self.constraints.max_position_size
        hi = self.constraints.max_position_size
        return [(lo, hi) for _ in range(n)]

    def _build_constraints(
        self,
        n: int,
        current_weights: np.ndarray,
    ) -> list[dict[str, Any]]:
        """Build scipy constraint dicts for sum-to-one, turnover, and leverage."""
        cons: list[dict[str, Any]] = []

        # Weights sum to 1
        cons.append({"type": "eq", "fun": lambda w: np.sum(w) - 1.0})

        # Turnover constraint
        if self.constraints.max_turnover < float("inf"):
            cons.append({
                "type": "ineq",
                "fun": lambda w, cw=current_weights: (
                    self.constraints.max_turnover - np.sum(np.abs(w - cw))
                ),
            })

        # Gross leverage constraint
        cons.append({
            "type": "ineq",
            "fun": lambda w: self.constraints.max_leverage - np.sum(np.abs(w)),
        })

        return cons

    def apply_sector_constraints(
        self,
        weights: dict[str, float],
    ) -> dict[str, float]:
        """Post-hoc enforcement of sector weight limits.

        Scales down positions in sectors that exceed
        ``max_sector_weight`` and redistributes to other sectors.
        """
        if not self.sector_map:
            return weights

        sector_weights: dict[str, float] = {}
        for sym, w in weights.items():
            sector = self.sector_map.get(sym, "other")
            sector_weights[sector] = sector_weights.get(sector, 0.0) + w

        adjusted = dict(weights)
        max_sw = self.constraints.max_sector_weight

        for sector, sw in sector_weights.items():
            if sw > max_sw:
                scale = max_sw / sw
                for sym in adjusted:
                    if self.sector_map.get(sym, "other") == sector:
                        adjusted[sym] *= scale

        # Renormalise
        total = sum(adjusted.values())
        if total > 1e-12:
            adjusted = {s: w / total for s, w in adjusted.items()}

        return adjusted


__all__ = [
    "PortfolioConstraints",
    "PortfolioAllocation",
    "PortfolioConstructor",
]
