"""Tests for Hierarchical Risk Parity optimizer."""

from __future__ import annotations

import numpy as np
import pandas as pd

from pyhron.portfolio.hrp import HRPOptimizer


def _make_returns(n_days: int = 252, n_assets: int = 10) -> pd.DataFrame:
    rng = np.random.default_rng(42)
    cols = [f"STOCK_{i}" for i in range(n_assets)]
    data = rng.normal(0.0005, 0.02, (n_days, n_assets))
    return pd.DataFrame(data, columns=cols)


class TestHRP:
    def test_weights_sum_to_one(self) -> None:
        hrp = HRPOptimizer()
        returns = _make_returns()
        weights = hrp.optimize(returns)
        total = sum(weights.values())
        assert abs(total - 1.0) < 1e-10

    def test_no_negative_weights(self) -> None:
        hrp = HRPOptimizer()
        returns = _make_returns()
        weights = hrp.optimize(returns)
        for w in weights.values():
            assert w >= -1e-10

    def test_determinism(self) -> None:
        """Same input produces same output."""
        returns = _make_returns()
        w1 = HRPOptimizer().optimize(returns)
        w2 = HRPOptimizer().optimize(returns)
        for sym in w1:
            assert abs(w1[sym] - w2[sym]) < 1e-12

    def test_with_singular_correlation(self) -> None:
        """Should handle near-singular matrices without raising."""
        rng = np.random.default_rng(42)
        # Create returns where two assets are nearly identical
        base = rng.normal(0, 0.02, (252, 1))
        data = np.hstack([base, base + 1e-10 * rng.normal(0, 1, (252, 1)), rng.normal(0, 0.02, (252, 3))])
        returns = pd.DataFrame(data, columns=["A", "B", "C", "D", "E"])

        hrp = HRPOptimizer()
        weights = hrp.optimize(returns)
        assert abs(sum(weights.values()) - 1.0) < 1e-10

    def test_all_symbols_present(self) -> None:
        returns = _make_returns(n_assets=5)
        hrp = HRPOptimizer()
        weights = hrp.optimize(returns)
        assert set(weights.keys()) == set(returns.columns)
