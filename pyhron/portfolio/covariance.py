"""Covariance matrix estimators for portfolio optimization.

Provides Ledoit-Wolf shrinkage and DCC-GARCH estimators tailored
for IDX equities.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Literal

import numpy as np

if TYPE_CHECKING:
    import pandas as pd


class LedoitWolfIDX:
    """Ledoit-Wolf shrinkage covariance estimator.

    Shrinks the sample covariance towards the identity matrix
    (scaled by average variance) using the analytical formula
    from Ledoit & Wolf (2004).
    """

    def fit(self, returns: pd.DataFrame) -> np.ndarray:
        """Estimate the shrinkage covariance matrix.

        Parameters
        ----------
        returns:
            (T × N) daily return matrix.

        Returns
        -------
        np.ndarray
            (N × N) shrinkage covariance matrix.
        """
        X = returns.values
        T, N = X.shape
        X_centered = X - X.mean(axis=0)
        sample_cov = X_centered.T @ X_centered / T

        # Target: scaled identity
        mu = np.trace(sample_cov) / N
        target = mu * np.eye(N)

        # Compute optimal shrinkage intensity
        delta = sample_cov - target
        sum_sq = np.sum(delta**2)

        # Analytical shrinkage coefficient
        Y = X_centered**2
        phi = np.sum((Y.T @ Y) / T - sample_cov**2)
        kappa = (phi / sum_sq) if sum_sq > 0 else 1.0
        shrinkage = max(0.0, min(1.0, kappa / T))

        return (1 - shrinkage) * sample_cov + shrinkage * target


class DynamicConditionalCorrelation:
    """DCC-GARCH(1,1) covariance estimator.

    Fits univariate GARCH(1,1) per asset, extracts standardised
    residuals, and applies DCC to reconstruct the full time-varying
    covariance matrix.
    """

    def fit(self, returns: pd.DataFrame) -> np.ndarray:
        """Estimate the DCC covariance matrix.

        Uses the ``arch`` library for univariate GARCH fitting.

        Parameters
        ----------
        returns:
            (T × N) daily return matrix.

        Returns
        -------
        np.ndarray
            (N × N) conditional covariance matrix at the last time step.
        """
        from arch import arch_model

        N = returns.shape[1]
        conditional_vols = np.zeros((len(returns), N))
        std_residuals = np.zeros_like(returns.values)

        for i, col in enumerate(returns.columns):
            series = returns[col].dropna() * 100  # Scale for GARCH
            if len(series) < 30:
                conditional_vols[:, i] = series.std()
                std_residuals[:, i] = returns[col].values / (series.std() / 100 + 1e-10)
                continue

            am = arch_model(series, vol="Garch", p=1, q=1, dist="normal", rescale=False)
            res = am.fit(disp="off", show_warning=False)

            # Conditional volatility
            cond_vol = res.conditional_volatility / 100
            conditional_vols[: len(cond_vol), i] = cond_vol.values

            # Standardised residuals
            resid = res.resid / 100
            std_res = resid / (cond_vol + 1e-10)
            std_residuals[: len(std_res), i] = std_res.values

        # Unconditional correlation of standardised residuals
        valid_rows = ~np.isnan(std_residuals).any(axis=1)
        std_valid = std_residuals[valid_rows]
        if len(std_valid) < 5:
            return np.cov(returns.values, rowvar=False)

        Q_bar = np.corrcoef(std_valid, rowvar=False)
        if Q_bar.ndim < 2:
            return np.cov(returns.values, rowvar=False)

        # DCC parameters (simplified fixed values)
        alpha = 0.05
        beta = 0.93

        Q_t = Q_bar.copy()
        for t in range(1, len(std_valid)):
            e_t = std_valid[t : t + 1].T
            Q_t = (1 - alpha - beta) * Q_bar + alpha * (e_t @ e_t.T) + beta * Q_t

        # Normalise to correlation
        D = np.sqrt(np.diag(Q_t))
        D_inv = np.diag(1.0 / (D + 1e-10))
        R_t = D_inv @ Q_t @ D_inv

        # Reconstruct covariance: D_sigma * R * D_sigma
        last_vols = conditional_vols[-1]
        D_sigma = np.diag(last_vols)
        return D_sigma @ R_t @ D_sigma


def get_covariance_estimator(
    method: Literal["ledoit_wolf", "dcc_garch"] = "ledoit_wolf",
) -> LedoitWolfIDX | DynamicConditionalCorrelation:
    """Factory for covariance estimators."""
    if method == "ledoit_wolf":
        return LedoitWolfIDX()
    if method == "dcc_garch":
        return DynamicConditionalCorrelation()
    msg = f"Unknown covariance method: {method}"
    raise ValueError(msg)
