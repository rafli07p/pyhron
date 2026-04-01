"""Advanced backtesting statistics.

Supplements the existing BacktestPerformanceMetrics with bootstrap
confidence intervals, deflated Sharpe ratio, probabilistic Sharpe
ratio, and other rigorous performance measures.
"""

from __future__ import annotations

import math

import numpy as np
import pandas as pd
from scipy.stats import norm

_EULER_MASCHERONI = 0.5772156649


def omega_ratio(returns: pd.Series, threshold: float = 0.0) -> float:
    r"""Omega ratio.

    .. math:: \Omega = \frac{E[\max(r - L, 0)]}{E[\max(L - r, 0)]}

    Parameters
    ----------
    returns:
        Return series.
    threshold:
        Minimum acceptable return ``L``.

    Returns
    -------
    float
        Omega ratio (> 1 is desirable).
    """
    excess = returns - threshold
    gains = excess[excess > 0].sum()
    losses = -excess[excess < 0].sum()
    if losses == 0:
        return float("inf") if gains > 0 else 1.0
    return float(gains / losses)


def calmar_ratio(returns: pd.Series, max_drawdown: float) -> float:
    """Calmar ratio: CAGR / |max_drawdown|.

    Parameters
    ----------
    returns:
        Daily return series.
    max_drawdown:
        Maximum drawdown as a positive fraction.

    Returns
    -------
    float
        Calmar ratio.
    """
    if max_drawdown == 0:
        return 0.0
    n_days = len(returns)
    if n_days < 2:
        return 0.0
    total_return = float((1 + returns).prod())
    years = n_days / 252
    cagr = total_return ** (1 / years) - 1 if years > 0 else 0.0
    return cagr / abs(max_drawdown)


def bootstrap_sharpe_ci(
    returns: pd.Series,
    n_bootstrap: int = 10_000,
    confidence: float = 0.95,
    block_size: int = 21,
) -> tuple[float, float, float]:
    """Bootstrap confidence interval for the Sharpe ratio.

    Uses stationary block bootstrap (Politis-Romano) to preserve
    autocorrelation structure.

    Parameters
    ----------
    returns:
        Daily return series.
    n_bootstrap:
        Number of bootstrap samples.
    confidence:
        Confidence level (default 0.95).
    block_size:
        Average block size for stationary bootstrap.

    Returns
    -------
    tuple
        (point_estimate, lower_ci, upper_ci).
    """
    point_sharpe = _sharpe(returns)

    rng = np.random.default_rng(42)
    n = len(returns)
    ret_arr = returns.values
    sharpe_samples = np.zeros(n_bootstrap)

    for i in range(n_bootstrap):
        # Stationary block bootstrap
        sample = np.empty(n)
        pos = 0
        idx = rng.integers(0, n)
        while pos < n:
            # Geometric block length
            block_len = rng.geometric(1.0 / block_size)
            end = min(pos + block_len, n)
            for j in range(pos, end):
                sample[j] = ret_arr[idx % n]
                idx += 1
            pos = end
            idx = rng.integers(0, n)

        sharpe_samples[i] = _sharpe(pd.Series(sample))

    alpha = (1 - confidence) / 2
    lower = float(np.percentile(sharpe_samples, alpha * 100))
    upper = float(np.percentile(sharpe_samples, (1 - alpha) * 100))

    return point_sharpe, lower, upper


def deflated_sharpe_ratio(
    sharpe_obs: float,
    n_trials: int,
    n_obs: int,
    sharpe_std: float,
) -> float:
    """Deflated Sharpe Ratio (Lopez de Prado & Bailey 2014).

    Adjusts the observed Sharpe ratio for multiple testing.

    .. math::

        DSR = \\Phi\\left[\\frac{SR_{obs} - E[SR_{max}]}{\\sigma[SR_{max}]}\\right]

    Parameters
    ----------
    sharpe_obs:
        Observed Sharpe ratio.
    n_trials:
        Number of strategy trials tested.
    n_obs:
        Number of observations.
    sharpe_std:
        Standard deviation of Sharpe ratio estimate.

    Returns
    -------
    float
        DSR probability in [0, 1].
    """
    if n_trials <= 0 or n_obs <= 0 or sharpe_std <= 0:
        return 0.0

    gamma = _EULER_MASCHERONI

    # E[SR_max] approximation
    e_sr_max = (1 - gamma) * norm.ppf(1 - 1 / n_trials) + gamma * norm.ppf(1 - 1 / (n_trials * math.e))

    std_sr_max = sharpe_std

    z = (sharpe_obs - e_sr_max) / std_sr_max if std_sr_max > 0 else 0.0
    return float(norm.cdf(z))


def probabilistic_sharpe_ratio(
    sharpe_obs: float,
    benchmark_sharpe: float,
    n_obs: int,
    skewness: float,
    kurtosis: float,
) -> float:
    """Probabilistic Sharpe Ratio (Bailey & Lopez de Prado).

    Probability that the true Sharpe exceeds the benchmark.

    Parameters
    ----------
    sharpe_obs:
        Observed Sharpe ratio.
    benchmark_sharpe:
        Benchmark Sharpe ratio to beat.
    n_obs:
        Number of return observations.
    skewness:
        Return series skewness.
    kurtosis:
        Return series excess kurtosis.

    Returns
    -------
    float
        PSR probability in [0, 1].
    """
    if n_obs <= 1:
        return 0.5

    sr_diff = sharpe_obs - benchmark_sharpe
    denominator = 1 - skewness * sharpe_obs + ((kurtosis - 1) / 4) * sharpe_obs**2
    if denominator <= 0:
        denominator = 1e-10

    z = sr_diff * math.sqrt(n_obs - 1) / math.sqrt(denominator)
    return float(norm.cdf(z))


def _sharpe(returns: pd.Series, rf_daily: float = 0.0) -> float:
    """Annualised Sharpe ratio."""
    excess = returns - rf_daily
    std = excess.std()
    if std == 0 or len(returns) < 2:
        return 0.0
    return float(excess.mean() / std * np.sqrt(252))
