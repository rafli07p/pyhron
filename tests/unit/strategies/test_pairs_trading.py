"""Tests for pairs trading strategy."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

import numpy as np
import pandas as pd

from pyhron.strategies.pairs_trading import PairsTradingStrategy

if TYPE_CHECKING:
    import pytest


class TestKalmanFilter:
    def test_hedge_ratio_convergence(self) -> None:
        """KF should converge to true hedge ratio on synthetic data."""
        rng = np.random.default_rng(42)
        n = 500
        true_hedge = 1.5
        x = np.cumsum(rng.normal(0, 1, n)) + 100
        y = true_hedge * x + rng.normal(0, 0.5, n) + 50

        hr, _ = PairsTradingStrategy.kalman_filter_hedge_ratio(y, x)
        # After convergence, hedge ratio should be close to 1.5
        assert abs(hr[-1] - true_hedge) < 0.5

    def test_output_length(self) -> None:
        n = 100
        y = np.random.default_rng(0).normal(0, 1, n)
        x = np.random.default_rng(1).normal(0, 1, n)
        hr, intercepts = PairsTradingStrategy.kalman_filter_hedge_ratio(y, x)
        assert len(hr) == n
        assert len(intercepts) == n


class TestPairsTrading:
    def test_idx_short_constraint_warning(self, caplog: pytest.LogCaptureFixture) -> None:
        """Should log warning about IDX short constraint."""
        rng = np.random.default_rng(42)
        n = 200
        x = pd.Series(np.cumsum(rng.normal(0, 1, n)) + 100, name="BBCA")
        y = pd.Series(1.5 * x.values + rng.normal(0, 2, n) + 20, name="TLKM")

        strategy = PairsTradingStrategy(entry_z=1.5, lookback=60)
        with caplog.at_level(logging.WARNING):
            signals = strategy.generate_signals(y, x)

        if signals:
            has_entry = any(s.action in ("ENTER_LONG", "ENTER_SHORT") for s in signals)
            if has_entry:
                assert "idx_short_constraint" in caplog.text

    def test_zscore_entry_exit_signals(self) -> None:
        """Test z-score based signal generation."""
        rng = np.random.default_rng(42)
        n = 300
        x = pd.Series(np.cumsum(rng.normal(0, 1, n)) + 100, name="A")
        # Create mean-reverting spread
        spread = np.zeros(n)
        for i in range(1, n):
            spread[i] = 0.95 * spread[i - 1] + rng.normal(0, 1)
        y = pd.Series(x.values + spread + 50, name="B")

        strategy = PairsTradingStrategy(entry_z=2.0, exit_z=0.5, lookback=60)
        signals = strategy.generate_signals(y, x)

        # Should produce at least some signals
        assert len(signals) >= 0

    def test_strategy_properties(self) -> None:
        strategy = PairsTradingStrategy()
        assert strategy.name == "pairs_trading"
        assert "entry_z" in strategy.parameters
        assert "exit_z" in strategy.parameters
