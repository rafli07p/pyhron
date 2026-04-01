"""Tests for Black-Litterman portfolio optimizer."""

from __future__ import annotations

import numpy as np

from pyhron.portfolio.black_litterman import BlackLittermanOptimizer


def _make_cov(n: int = 5) -> np.ndarray:
    rng = np.random.default_rng(42)
    A = rng.normal(0, 0.01, (n, n))
    return A.T @ A + np.eye(n) * 0.001


class TestBlackLitterman:
    def test_posterior_shape_and_finite(self) -> None:
        bl = BlackLittermanOptimizer()
        sigma = _make_cov(5)
        w_mkt = np.ones(5) / 5
        mu = bl.compute_posterior(sigma, w_mkt)
        assert mu.shape == (5,)
        assert np.all(np.isfinite(mu))

    def test_long_only_constraint(self) -> None:
        bl = BlackLittermanOptimizer()
        sigma = _make_cov(5)
        w_mkt = np.ones(5) / 5
        mu = bl.compute_posterior(sigma, w_mkt)
        result = bl.optimize(
            symbols=["A", "B", "C", "D", "E"],
            sigma=sigma,
            mu=mu,
            max_weight=0.5,
            min_weight=0.0,
        )
        for w in result.weights.values():
            assert w >= -1e-10  # Essentially non-negative

    def test_max_weight_cap(self) -> None:
        n = 10  # 10 assets: 1/10 = 0.1 < 0.15, so cap is feasible
        bl = BlackLittermanOptimizer()
        sigma = _make_cov(n)
        w_mkt = np.ones(n) / n
        mu = bl.compute_posterior(sigma, w_mkt)
        symbols = [f"S{i}" for i in range(n)]
        result = bl.optimize(
            symbols=symbols,
            sigma=sigma,
            mu=mu,
            max_weight=0.15,
        )
        for w in result.weights.values():
            assert w <= 0.15 + 1e-6

    def test_zero_views_reverts_to_equilibrium(self) -> None:
        """With no views, posterior should equal equilibrium returns."""
        bl = BlackLittermanOptimizer()
        sigma = _make_cov(5)
        w_mkt = np.array([0.3, 0.25, 0.2, 0.15, 0.1])

        mu_no_views = bl.compute_posterior(sigma, w_mkt)
        pi = bl._delta * sigma @ w_mkt
        np.testing.assert_allclose(mu_no_views, pi, rtol=1e-10)

    def test_weights_sum_to_one(self) -> None:
        bl = BlackLittermanOptimizer()
        sigma = _make_cov(5)
        w_mkt = np.ones(5) / 5
        mu = bl.compute_posterior(sigma, w_mkt)
        result = bl.optimize(
            symbols=["A", "B", "C", "D", "E"],
            sigma=sigma,
            mu=mu,
        )
        total = sum(result.weights.values())
        assert abs(total - 1.0) < 1e-6

    def test_with_views(self) -> None:
        bl = BlackLittermanOptimizer()
        sigma = _make_cov(5)
        w_mkt = np.ones(5) / 5

        P = np.zeros((1, 5))
        P[0, 0] = 1.0  # Bullish view on asset 0
        q = np.array([0.20])
        omega = np.array([[0.01]])

        mu = bl.compute_posterior(sigma, w_mkt, P, q, omega)
        assert mu[0] > bl.compute_posterior(sigma, w_mkt)[0]
