"""Black-Litterman portfolio optimization model.

Combines market equilibrium returns with quantitative views
from the ML signal pipeline to produce posterior expected returns,
then solves mean-variance optimization with IDX constraints.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

import numpy as np
from scipy.optimize import minimize


@dataclass(frozen=True)
class OptimalWeights:
    """Result of portfolio optimization.

    Attributes
    ----------
    weights:
        Asset weights (sum to 1.0).
    expected_return:
        Annualised expected return of the portfolio.
    expected_vol:
        Annualised expected volatility.
    sharpe_estimate:
        Estimated Sharpe ratio.
    """

    weights: dict[str, float]
    expected_return: float
    expected_vol: float
    sharpe_estimate: float


# Regime-specific risk aversion values
REGIME_RISK_AVERSION: dict[str, float] = {
    "bull": 2.5,
    "bear": 5.0,
    "sideways": 3.5,
}


class BlackLittermanOptimizer:
    """Black-Litterman model with IDX constraints.

    Parameters
    ----------
    tau:
        Scalar controlling uncertainty in equilibrium (default 0.05).
    risk_aversion:
        Risk aversion parameter delta (or from regime).
    regime:
        Market regime for automatic risk aversion setting.
    """

    def __init__(
        self,
        tau: float = 0.05,
        risk_aversion: float | None = None,
        regime: Literal["bull", "bear", "sideways"] = "sideways",
    ) -> None:
        self._tau = tau
        self._delta = risk_aversion or REGIME_RISK_AVERSION.get(regime, 3.5)

    def compute_posterior(
        self,
        sigma: np.ndarray,
        market_weights: np.ndarray,
        P: np.ndarray | None = None,  # noqa: N803
        q: np.ndarray | None = None,
        omega: np.ndarray | None = None,
    ) -> np.ndarray:
        """Compute Black-Litterman posterior expected returns.

        Parameters
        ----------
        sigma:
            (N × N) covariance matrix.
        market_weights:
            (N,) market-cap weights.
        P:
            (K × N) views picking matrix.
        q:
            (K,) expected returns for views.
        omega:
            (K × K) diagonal view uncertainty.

        Returns
        -------
        np.ndarray
            (N,) posterior expected returns.
        """
        # Equilibrium returns: Pi = delta * Sigma * w_mkt
        pi = self._delta * sigma @ market_weights

        if P is None or q is None:
            return pi

        tau_sigma = self._tau * sigma
        tau_sigma_inv = np.linalg.inv(tau_sigma)

        if omega is None:
            omega = np.diag(np.diag(P @ tau_sigma @ P.T))

        omega_inv = np.linalg.inv(omega)

        # Posterior: mu_BL = (tau_sigma_inv + P'Omega_inv P)^{-1} * (tau_sigma_inv * Pi + P'Omega_inv q)
        M = tau_sigma_inv + P.T @ omega_inv @ P
        v = tau_sigma_inv @ pi + P.T @ omega_inv @ q

        return np.linalg.solve(M, v)

    def optimize(
        self,
        symbols: list[str],
        sigma: np.ndarray,
        mu: np.ndarray,
        max_weight: float = 0.15,
        min_weight: float = 0.0,
    ) -> OptimalWeights:
        """Mean-variance optimization on posterior returns.

        Parameters
        ----------
        symbols:
            Asset names.
        sigma:
            (N × N) covariance matrix.
        mu:
            (N,) expected returns.
        max_weight:
            Maximum weight per asset (IDX: 15%).
        min_weight:
            Minimum weight per asset.

        Returns
        -------
        OptimalWeights
        """
        n = len(symbols)

        # Ensure feasibility: max_weight must allow sum to 1.0
        effective_max = max(max_weight, 1.0 / n)

        def neg_utility(w: np.ndarray) -> float:
            ret = w @ mu
            risk = w @ sigma @ w
            return -(ret - (self._delta / 2) * risk)

        constraints = [
            {"type": "eq", "fun": lambda w: np.sum(w) - 1.0},
        ]
        bounds = [(min_weight, effective_max)] * n
        x0 = np.ones(n) / n

        result = minimize(
            neg_utility,
            x0,
            method="SLSQP",
            bounds=bounds,
            constraints=constraints,
            options={"maxiter": 1000, "ftol": 1e-12},
        )

        w = result.x
        w = np.maximum(w, 0)
        w = w / w.sum()

        # Enforce max weight with iterative redistribution
        for _ in range(20):
            excess = np.maximum(w - effective_max, 0)
            if excess.sum() < 1e-12:
                break
            w = np.minimum(w, effective_max)
            total_excess = excess.sum()
            uncapped_mask = w < effective_max - 1e-10
            if uncapped_mask.any():
                redistribute = min(total_excess, (effective_max - w[uncapped_mask]).sum())
                proportions = (effective_max - w[uncapped_mask]) / (effective_max - w[uncapped_mask]).sum()
                w[uncapped_mask] += proportions * redistribute
            else:
                w = w / w.sum()
                break

        exp_ret = float(w @ mu)
        exp_vol = float(np.sqrt(w @ sigma @ w))
        sharpe = exp_ret / exp_vol if exp_vol > 0 else 0.0

        weights_dict = {s: float(w[i]) for i, s in enumerate(symbols)}

        return OptimalWeights(
            weights=weights_dict,
            expected_return=exp_ret,
            expected_vol=exp_vol,
            sharpe_estimate=sharpe,
        )

    def build_views_from_signals(
        self,
        symbols: list[str],
        scores: dict[str, float],
        mu_view: float = 0.10,
    ) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
        """Construct BL views from XGBRanker signal scores.

        Top quintile → absolute view E[r] = mu_view.
        Bottom quintile → E[r] = -mu_view.

        Parameters
        ----------
        symbols:
            Asset names in order.
        scores:
            Signal scores per symbol.
        mu_view:
            Annualised expected return for views.

        Returns
        -------
        tuple
            (P, q, omega) matrices.
        """
        n = len(symbols)
        sorted_scores = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        quintile_size = max(1, n // 5)

        top = [s for s, _ in sorted_scores[:quintile_size]]
        bottom = [s for s, _ in sorted_scores[-quintile_size:]]

        views: list[tuple[np.ndarray, float, float]] = []

        for sym in top:
            if sym in symbols:
                idx = symbols.index(sym)
                pick = np.zeros(n)
                pick[idx] = 1.0
                score = abs(scores.get(sym, 0))
                uncertainty = (1 - score) if score < 1 else 0.1
                views.append((pick, mu_view, uncertainty * mu_view**2))

        for sym in bottom:
            if sym in symbols:
                idx = symbols.index(sym)
                pick = np.zeros(n)
                pick[idx] = 1.0
                score = abs(scores.get(sym, 0))
                uncertainty = (1 - score) if score < 1 else 0.1
                views.append((pick, -mu_view, uncertainty * mu_view**2))

        if not views:
            return np.zeros((0, n)), np.zeros(0), np.zeros((0, 0))

        P = np.array([v[0] for v in views])
        q = np.array([v[1] for v in views])
        omega = np.diag([v[2] for v in views])

        return P, q, omega
