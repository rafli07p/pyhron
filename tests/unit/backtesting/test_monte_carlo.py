"""Tests for Monte Carlo simulation."""

from __future__ import annotations

import numpy as np
import pandas as pd

from pyhron.backtesting.monte_carlo import MonteCarloSimulator


def _make_returns(n: int = 252) -> pd.Series:
    rng = np.random.default_rng(42)
    return pd.Series(rng.normal(0.0005, 0.02, n))


class TestGBM:
    def test_shape(self) -> None:
        sim = MonteCarloSimulator(_make_returns(), n_simulations=100)
        paths = sim.simulate_gbm(60)
        assert paths.shape == (100, 60)

    def test_all_positive(self) -> None:
        """GBM paths should be positive (they're prices)."""
        sim = MonteCarloSimulator(_make_returns(), n_simulations=100)
        paths = sim.simulate_gbm(60)
        assert np.all(paths > 0)


class TestBlockBootstrap:
    def test_shape(self) -> None:
        sim = MonteCarloSimulator(_make_returns(), n_simulations=50)
        paths = sim.simulate_block_bootstrap(60, block_size=21)
        assert paths.shape == (50, 60)


class TestVaRCVaR:
    def test_var_lt_cvar(self) -> None:
        """VaR should be less negative than CVaR (CVaR is worse)."""
        sim = MonteCarloSimulator(_make_returns(), n_simulations=1000)
        var, cvar = sim.var_cvar(confidence=0.95)
        assert var >= cvar  # Both negative; var closer to 0

    def test_values_are_reasonable(self) -> None:
        sim = MonteCarloSimulator(_make_returns(), n_simulations=1000)
        var, cvar = sim.var_cvar()
        assert -2.0 < var < 2.0
        assert -2.0 < cvar < 2.0


class TestMaxDrawdownDistribution:
    def test_no_positive_values(self) -> None:
        """All max drawdowns should be non-positive."""
        sim = MonteCarloSimulator(_make_returns(), n_simulations=100)
        dd = sim.max_drawdown_distribution()
        assert (dd <= 0).all()

    def test_shape(self) -> None:
        sim = MonteCarloSimulator(_make_returns(), n_simulations=100)
        dd = sim.max_drawdown_distribution()
        assert len(dd) == 100
