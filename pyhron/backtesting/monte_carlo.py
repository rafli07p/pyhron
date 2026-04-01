"""Monte Carlo simulation for backtesting.

Provides GBM and block bootstrap simulation for equity curves,
VaR/CVaR, max drawdown distribution, and fan chart visualisation.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd


class MonteCarloSimulator:
    """Monte Carlo simulator for strategy returns.

    Parameters
    ----------
    strategy_returns:
        Historical daily return series.
    n_simulations:
        Number of Monte Carlo paths.
    """

    def __init__(
        self,
        strategy_returns: pd.Series,
        n_simulations: int = 10_000,
    ) -> None:
        self._returns = strategy_returns.values.astype(float)
        self._n_sims = n_simulations
        self._mu = float(np.mean(self._returns))
        self._sigma = float(np.std(self._returns))
        self._rng = np.random.default_rng(42)

    def simulate_gbm(self, horizon_days: int) -> np.ndarray:
        """Simulate GBM (Geometric Brownian Motion) paths.

        Parameters
        ----------
        horizon_days:
            Number of days to simulate.

        Returns
        -------
        np.ndarray
            Shape ``(n_simulations, horizon_days)`` of cumulative returns.
        """
        dt = 1.0
        drift = (self._mu - 0.5 * self._sigma**2) * dt
        diffusion = self._sigma * np.sqrt(dt) * self._rng.standard_normal((self._n_sims, horizon_days))
        log_returns = drift + diffusion
        return np.exp(np.cumsum(log_returns, axis=1))

    def simulate_block_bootstrap(
        self,
        horizon_days: int,
        block_size: int = 21,
    ) -> np.ndarray:
        """Stationary block bootstrap simulation.

        Preserves autocorrelation structure of returns.

        Parameters
        ----------
        horizon_days:
            Number of days to simulate.
        block_size:
            Average block length.

        Returns
        -------
        np.ndarray
            Shape ``(n_simulations, horizon_days)`` of cumulative returns.
        """
        n = len(self._returns)
        paths = np.zeros((self._n_sims, horizon_days))

        for sim in range(self._n_sims):
            sample = np.empty(horizon_days)
            pos = 0
            idx = self._rng.integers(0, n)

            while pos < horizon_days:
                block_len = self._rng.geometric(1.0 / block_size)
                end = min(pos + block_len, horizon_days)
                for j in range(pos, end):
                    sample[j] = self._returns[idx % n]
                    idx += 1
                pos = end
                idx = self._rng.integers(0, n)

            paths[sim] = np.cumprod(1 + sample)

        return paths

    def var_cvar(self, confidence: float = 0.95) -> tuple[float, float]:
        """Parametric VaR and CVaR on simulated terminal returns.

        Parameters
        ----------
        confidence:
            Confidence level (e.g. 0.95).

        Returns
        -------
        tuple
            (VaR, CVaR) as negative numbers (losses).
        """
        paths = self.simulate_gbm(252)
        terminal_returns = paths[:, -1] - 1.0

        var = float(np.percentile(terminal_returns, (1 - confidence) * 100))
        cvar = float(terminal_returns[terminal_returns <= var].mean())

        return var, cvar

    def max_drawdown_distribution(self) -> pd.Series:
        """Distribution of max drawdown across simulation paths.

        Returns
        -------
        pd.Series
            Max drawdown per simulation (negative values).
        """
        paths = self.simulate_gbm(252)
        drawdowns = np.zeros(self._n_sims)

        for i in range(self._n_sims):
            equity = paths[i]
            running_max = np.maximum.accumulate(equity)
            dd = (equity - running_max) / running_max
            drawdowns[i] = float(dd.min())

        return pd.Series(drawdowns, name="max_drawdown")

    def plot_fan_chart(
        self,
        save_path: Path,
        percentiles: list[int] | None = None,
    ) -> None:
        """Plot fan chart of equity curves.

        Parameters
        ----------
        save_path:
            File path to save the figure.
        percentiles:
            Percentile levels to show (default [5, 25, 50, 75, 95]).
        """
        import matplotlib

        matplotlib.use("Agg")
        import matplotlib.pyplot as plt

        if percentiles is None:
            percentiles = [5, 25, 50, 75, 95]

        paths = self.simulate_gbm(252)

        fig, ax = plt.subplots(figsize=(12, 6))

        for pct in percentiles:
            line = np.percentile(paths, pct, axis=0)
            ax.plot(line, label=f"{pct}th percentile", alpha=0.7)

        # Fill between 25-75
        p25 = np.percentile(paths, 25, axis=0)
        p75 = np.percentile(paths, 75, axis=0)
        ax.fill_between(range(len(p25)), p25, p75, alpha=0.2, color="blue")

        ax.set_xlabel("Days")
        ax.set_ylabel("Cumulative Return")
        ax.set_title("Monte Carlo Fan Chart")
        ax.legend()
        fig.tight_layout()
        fig.savefig(save_path, dpi=150)
        plt.close(fig)
