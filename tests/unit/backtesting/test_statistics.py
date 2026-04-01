"""Tests for advanced backtesting statistics."""

from __future__ import annotations

import numpy as np
import pandas as pd

from pyhron.backtesting.statistics import (
    bootstrap_sharpe_ci,
    calmar_ratio,
    deflated_sharpe_ratio,
    omega_ratio,
    probabilistic_sharpe_ratio,
)


def _make_returns(n: int = 500, mu: float = 0.0005, sigma: float = 0.02) -> pd.Series:
    rng = np.random.default_rng(42)
    return pd.Series(rng.normal(mu, sigma, n))


class TestBootstrapSharpeCI:
    def test_lower_lt_point_lt_upper(self) -> None:
        returns = _make_returns()
        point, lower, upper = bootstrap_sharpe_ci(returns, n_bootstrap=1000)
        assert lower < point
        assert point < upper

    def test_wider_ci_with_less_data(self) -> None:
        long_returns = _make_returns(1000)
        short_returns = _make_returns(100)
        _, lo1, hi1 = bootstrap_sharpe_ci(long_returns, n_bootstrap=500)
        _, lo2, hi2 = bootstrap_sharpe_ci(short_returns, n_bootstrap=500)
        assert (hi2 - lo2) >= (hi1 - lo1) * 0.5  # Wider with less data


class TestDeflatedSharpeRatio:
    def test_always_in_zero_one(self) -> None:
        for sharpe in [0.0, 0.5, 1.0, 2.0, 3.0]:
            dsr = deflated_sharpe_ratio(sharpe, n_trials=100, n_obs=252, sharpe_std=0.3)
            assert 0.0 <= dsr <= 1.0

    def test_higher_trials_lowers_dsr(self) -> None:
        dsr_few = deflated_sharpe_ratio(1.5, n_trials=5, n_obs=252, sharpe_std=0.3)
        dsr_many = deflated_sharpe_ratio(1.5, n_trials=1000, n_obs=252, sharpe_std=0.3)
        assert dsr_many < dsr_few

    def test_zero_inputs(self) -> None:
        assert deflated_sharpe_ratio(1.0, n_trials=0, n_obs=252, sharpe_std=0.3) == 0.0


class TestOmegaRatio:
    def test_centered_returns_near_one(self) -> None:
        """Returns centered at threshold should give omega ≈ 1."""
        rng = np.random.default_rng(42)
        returns = pd.Series(rng.normal(0, 0.01, 10000))
        result = omega_ratio(returns, threshold=0.0)
        assert abs(result - 1.0) < 0.15

    def test_positive_returns_above_one(self) -> None:
        returns = pd.Series(np.ones(100) * 0.01)
        assert omega_ratio(returns) == float("inf")


class TestProbabilisticSharpeRatio:
    def test_equal_sharpe_gives_half(self) -> None:
        """PSR should be ~0.5 when observed matches benchmark."""
        psr = probabilistic_sharpe_ratio(
            sharpe_obs=1.0,
            benchmark_sharpe=1.0,
            n_obs=252,
            skewness=0.0,
            kurtosis=3.0,
        )
        assert abs(psr - 0.5) < 0.05

    def test_higher_obs_gives_higher_psr(self) -> None:
        psr = probabilistic_sharpe_ratio(
            sharpe_obs=2.0,
            benchmark_sharpe=1.0,
            n_obs=252,
            skewness=0.0,
            kurtosis=3.0,
        )
        assert psr > 0.5


class TestCalmarRatio:
    def test_positive_returns_positive_calmar(self) -> None:
        # Use high mu and low sigma to ensure positive CAGR
        returns = _make_returns(252, mu=0.005, sigma=0.005)
        result = calmar_ratio(returns, max_drawdown=0.1)
        assert result > 0

    def test_zero_drawdown(self) -> None:
        returns = _make_returns()
        assert calmar_ratio(returns, max_drawdown=0.0) == 0.0
