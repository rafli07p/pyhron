"""Unified portfolio optimizer interface.

Supports Black-Litterman, HRP, and equal-weight allocation
with IDX-specific constraints.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Literal

import numpy as np

from pyhron.portfolio.black_litterman import BlackLittermanOptimizer, OptimalWeights
from pyhron.portfolio.covariance import LedoitWolfIDX
from pyhron.portfolio.hrp import HRPOptimizer

if TYPE_CHECKING:
    import pandas as pd


class PortfolioOptimizer:
    """Unified portfolio optimization interface.

    Parameters
    ----------
    method:
        Optimization method.
    regime:
        Market regime for Black-Litterman risk aversion.
    """

    def __init__(
        self,
        method: Literal["black_litterman", "hrp", "equal_weight"] = "black_litterman",
        regime: Literal["bull", "bear", "sideways"] = "sideways",
    ) -> None:
        self._method = method
        self._regime = regime

    def optimize(
        self,
        universe: list[str],
        returns: pd.DataFrame,
        signals: dict[str, float] | None = None,
        market_weights: dict[str, float] | None = None,
        max_weight: float = 0.15,
        min_weight: float = 0.01,
        target_volatility: float | None = None,
        prior_weights: dict[str, float] | None = None,
    ) -> OptimalWeights:
        """Optimize portfolio weights.

        Parameters
        ----------
        universe:
            List of ticker symbols.
        returns:
            Historical returns DataFrame (T × N).
        signals:
            XGBRanker signal scores per symbol.
        market_weights:
            Market-cap weights for Black-Litterman.
        max_weight:
            Maximum weight per asset (IDX: 15%).
        min_weight:
            Minimum weight per asset.
        target_volatility:
            If set, scale weights to hit this vol target.
        prior_weights:
            Previous weights for turnover penalty.

        Returns
        -------
        OptimalWeights
        """
        # Ensure returns only has symbols in universe
        available = [s for s in universe if s in returns.columns]
        if not available:
            return OptimalWeights(weights={}, expected_return=0.0, expected_vol=0.0, sharpe_estimate=0.0)
        ret = returns[available]

        if self._method == "equal_weight":
            return self._equal_weight(available)

        if self._method == "hrp":
            return self._hrp(available, ret, max_weight)

        # Black-Litterman
        return self._black_litterman(
            available,
            ret,
            signals,
            market_weights,
            max_weight,
            min_weight,
        )

    def _equal_weight(self, symbols: list[str]) -> OptimalWeights:
        n = len(symbols)
        w = 1.0 / n
        return OptimalWeights(
            weights={s: w for s in symbols},
            expected_return=0.0,
            expected_vol=0.0,
            sharpe_estimate=0.0,
        )

    def _hrp(
        self,
        symbols: list[str],
        returns: pd.DataFrame,
        max_weight: float,
    ) -> OptimalWeights:
        hrp = HRPOptimizer()
        weights = hrp.optimize(returns)

        # Enforce max weight cap
        weights = self._cap_weights(weights, max_weight)

        cov = LedoitWolfIDX().fit(returns)
        w_arr = np.array([weights.get(s, 0) for s in symbols])
        mu = returns.mean().values * 252
        exp_ret = float(w_arr @ mu)
        exp_vol = float(np.sqrt(w_arr @ cov @ w_arr) * np.sqrt(252))
        sharpe = exp_ret / exp_vol if exp_vol > 0 else 0.0

        return OptimalWeights(
            weights=weights,
            expected_return=exp_ret,
            expected_vol=exp_vol,
            sharpe_estimate=sharpe,
        )

    def _black_litterman(
        self,
        symbols: list[str],
        returns: pd.DataFrame,
        signals: dict[str, float] | None,
        market_weights: dict[str, float] | None,
        max_weight: float,
        min_weight: float,
    ) -> OptimalWeights:
        cov = LedoitWolfIDX().fit(returns)
        n = len(symbols)

        # Market weights
        if market_weights:
            w_mkt = np.array([market_weights.get(s, 1.0 / n) for s in symbols])
        else:
            w_mkt = np.ones(n) / n
        w_mkt = w_mkt / w_mkt.sum()

        bl = BlackLittermanOptimizer(regime=self._regime)

        # Build views from signals
        P, q, omega = None, None, None
        if signals:
            P, q, omega = bl.build_views_from_signals(symbols, signals)
            if len(q) == 0:
                P, q, omega = None, None, None

        mu_bl = bl.compute_posterior(cov, w_mkt, P, q, omega)

        return bl.optimize(symbols, cov, mu_bl, max_weight, min_weight)

    @staticmethod
    def _cap_weights(weights: dict[str, float], max_weight: float) -> dict[str, float]:
        """Enforce maximum weight constraint with redistribution."""
        result = dict(weights)
        excess = 0.0
        uncapped = []

        for s, w in result.items():
            if w > max_weight:
                excess += w - max_weight
                result[s] = max_weight
            else:
                uncapped.append(s)

        if excess > 0 and uncapped:
            per_stock = excess / len(uncapped)
            for s in uncapped:
                result[s] += per_stock

        total = sum(result.values())
        if total > 0:
            result = {s: w / total for s, w in result.items()}

        return result
