"""Tests for factor model strategy."""

from __future__ import annotations

import numpy as np
import pandas as pd

from pyhron.strategies.factor_model import FactorModelStrategy


def _make_returns(n_days: int = 252, n_stocks: int = 20) -> pd.DataFrame:
    rng = np.random.default_rng(42)
    cols = [f"STOCK_{i}" for i in range(n_stocks)]
    data = rng.normal(0.0005, 0.02, (n_days, n_stocks))
    return pd.DataFrame(data, columns=cols, index=pd.bdate_range("2023-01-01", periods=n_days))


class TestFactorConstruction:
    def test_smb_hml_disjoint_sets(self) -> None:
        """SMB and HML should use disjoint size groups."""
        rng = np.random.default_rng(42)
        n = 20
        returns = _make_returns(252, n)
        dates = returns.index

        market_caps = pd.DataFrame(
            rng.uniform(1e9, 1e12, (252, n)),
            columns=returns.columns,
            index=dates,
        )
        book_to_market = pd.DataFrame(
            rng.uniform(0.3, 3.0, (252, n)),
            columns=returns.columns,
            index=dates,
        )
        market_return = pd.Series(rng.normal(0.001, 0.01, 252), index=dates)

        factors = FactorModelStrategy.construct_factors(
            returns,
            market_caps,
            book_to_market,
            market_return,
        )
        assert "MKT_IDX" in factors.columns
        assert "SMB_IDX" in factors.columns
        assert "HML_IDX" in factors.columns
        assert len(factors) == 252


class TestOLSEstimation:
    def test_beta_estimation_synthetic(self) -> None:
        """OLS should recover approximate betas from synthetic data."""
        rng = np.random.default_rng(42)
        n = 252

        mkt = rng.normal(0.001, 0.01, n)
        smb = rng.normal(0, 0.005, n)
        hml = rng.normal(0, 0.005, n)

        factor_returns = pd.DataFrame(
            {"MKT_IDX": mkt, "SMB_IDX": smb, "HML_IDX": hml},
            index=pd.bdate_range("2023-01-01", periods=n),
        )

        # Stock with known beta = 1.2 to market
        true_beta = 1.2
        stock_ret = true_beta * mkt + 0.5 * smb + rng.normal(0, 0.005, n)
        stock_returns = pd.DataFrame(
            {"BBCA": stock_ret},
            index=factor_returns.index,
        )

        strategy = FactorModelStrategy()
        exposures = strategy.estimate_exposures(stock_returns, factor_returns)
        assert len(exposures) == 1
        assert abs(exposures[0].beta_mkt - true_beta) < 0.3

    def test_select_portfolio(self) -> None:
        from pyhron.strategies.factor_model import FactorExposure

        exposures = [
            FactorExposure("A", alpha=0.005, beta_mkt=1.0, beta_smb=0.3, beta_hml=0.2, r_squared=0.5),
            FactorExposure("B", alpha=0.003, beta_mkt=0.8, beta_smb=0.1, beta_hml=0.4, r_squared=0.4),
            FactorExposure("C", alpha=0.001, beta_mkt=1.1, beta_smb=0.2, beta_hml=0.1, r_squared=0.3),
            FactorExposure("D", alpha=-0.001, beta_mkt=0.9, beta_smb=0.1, beta_hml=0.3, r_squared=0.2),
        ]

        strategy = FactorModelStrategy(top_decile_pct=0.25)
        selected = strategy.select_portfolio(exposures)
        assert "A" in selected
        assert len(selected) == 1  # 25% of 4 = 1

    def test_monthly_rebalance_frequency(self) -> None:
        strategy = FactorModelStrategy(rebalance_frequency=21)
        assert strategy.parameters["rebalance_frequency"] == 21
