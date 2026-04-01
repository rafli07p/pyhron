"""Statistical arbitrage: cointegration-based pairs trading.

Kalman Filter spread estimation with z-score entry/exit signals.
IDX long-only constraint: short legs are expressed as underweights.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


@dataclass
class PairSignal:
    """Signal for a pairs trade."""

    symbol_long: str
    symbol_short: str
    z_score: float
    hedge_ratio: float
    action: str  # "ENTER_LONG", "ENTER_SHORT", "EXIT"
    kelly_fraction: float


class PairsTradingStrategy:
    """Cointegration-based pairs trading strategy.

    Parameters
    ----------
    entry_z:
        Z-score threshold for entry (default 2.0).
    exit_z:
        Z-score threshold for exit (default 0.5).
    lookback:
        Rolling window for z-score (default 60 days).
    max_position_pct:
        Maximum NAV per leg (default 0.05 = 5%).
    name:
        Strategy name.
    """

    def __init__(
        self,
        entry_z: float = 2.0,
        exit_z: float = 0.5,
        lookback: int = 60,
        max_position_pct: float = 0.05,
        name: str = "pairs_trading",
    ) -> None:
        self._entry_z = entry_z
        self._exit_z = exit_z
        self._lookback = lookback
        self._max_position_pct = max_position_pct
        self._name = name

    @property
    def name(self) -> str:
        return self._name

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "entry_z": self._entry_z,
            "exit_z": self._exit_z,
            "lookback": self._lookback,
            "max_position_pct": self._max_position_pct,
        }

    @staticmethod
    def find_cointegrated_pairs(
        prices: pd.DataFrame,
        p_threshold: float = 0.05,
    ) -> list[tuple[str, str, float]]:
        """Find cointegrated pairs using Engle-Granger test.

        Parameters
        ----------
        prices:
            DataFrame with columns as symbols, rows as dates.
        p_threshold:
            Maximum p-value for cointegration.

        Returns
        -------
        list[tuple]
            (symbol_a, symbol_b, p_value) for cointegrated pairs.
        """
        from statsmodels.tsa.stattools import coint

        symbols = list(prices.columns)
        pairs: list[tuple[str, str, float]] = []

        for i in range(len(symbols)):
            for j in range(i + 1, len(symbols)):
                s1 = prices[symbols[i]].dropna()
                s2 = prices[symbols[j]].dropna()
                common_idx = s1.index.intersection(s2.index)
                if len(common_idx) < 60:
                    continue
                try:
                    _, p_value, _ = coint(s1.loc[common_idx], s2.loc[common_idx])
                    if p_value < p_threshold:
                        pairs.append((symbols[i], symbols[j], float(p_value)))
                except Exception:  # noqa: S112
                    continue

        return sorted(pairs, key=lambda x: x[2])

    @staticmethod
    def kalman_filter_hedge_ratio(
        y: np.ndarray,
        x: np.ndarray,
        Q_diag: tuple[float, float] = (1e-5, 1e-4),  # noqa: N803
        R: float = 1e-3,  # noqa: N803
    ) -> tuple[np.ndarray, np.ndarray]:
        """Estimate time-varying hedge ratio using Kalman Filter.

        State: [hedge_ratio, intercept]
        Observation: y_t = hedge_ratio * x_t + intercept + eps

        Parameters
        ----------
        y:
            Dependent price series.
        x:
            Independent price series.
        Q_diag:
            Process noise diagonal.
        R:
            Observation noise.

        Returns
        -------
        tuple
            (hedge_ratios, intercepts) arrays.
        """
        n = len(y)
        # State: [hedge_ratio, intercept]
        state = np.array([0.0, 0.0])
        P = np.eye(2) * 1.0
        Q = np.diag(Q_diag)

        hedge_ratios = np.zeros(n)
        intercepts = np.zeros(n)

        for t in range(n):
            # Predict
            state_pred = state
            P_pred = P + Q

            # Update
            H = np.array([x[t], 1.0])
            y_pred = H @ state_pred
            residual = y[t] - y_pred
            S = H @ P_pred @ H + R
            K = P_pred @ H / S

            state = state_pred + K * residual
            P = (np.eye(2) - np.outer(K, H)) @ P_pred

            hedge_ratios[t] = state[0]
            intercepts[t] = state[1]

        return hedge_ratios, intercepts

    def generate_signals(
        self,
        y_prices: pd.Series,
        x_prices: pd.Series,
    ) -> list[PairSignal]:
        """Generate pair trading signals.

        Parameters
        ----------
        y_prices:
            Dependent asset prices.
        x_prices:
            Independent asset prices.

        Returns
        -------
        list[PairSignal]
            Trade signals.
        """
        y_name = y_prices.name or "Y"
        x_name = x_prices.name or "X"

        y_arr = y_prices.values.astype(float)
        x_arr = x_prices.values.astype(float)

        hedge_ratios, intercepts = self.kalman_filter_hedge_ratio(y_arr, x_arr)

        # Compute spread
        spread = y_arr - hedge_ratios * x_arr - intercepts

        if len(spread) < self._lookback:
            return []

        # Rolling z-score
        spread_series = pd.Series(spread)
        mu = spread_series.rolling(self._lookback).mean()
        sigma = spread_series.rolling(self._lookback).std()

        signals: list[PairSignal] = []

        for t in range(self._lookback, len(spread)):
            if sigma.iloc[t] == 0 or np.isnan(sigma.iloc[t]):
                continue

            z = (spread[t] - mu.iloc[t]) / sigma.iloc[t]
            hr = hedge_ratios[t]

            # Kelly fraction: f* = 0.5 * mu/sigma^2
            mu_val = float(mu.iloc[t])
            sig_val = float(sigma.iloc[t])
            kelly = min(0.5 * abs(mu_val) / (sig_val**2 + 1e-10), self._max_position_pct)

            if z < -self._entry_z:
                signals.append(
                    PairSignal(
                        symbol_long=str(y_name),
                        symbol_short=str(x_name),
                        z_score=float(z),
                        hedge_ratio=float(hr),
                        action="ENTER_LONG",
                        kelly_fraction=kelly,
                    )
                )
                # IDX: short leg cannot be expressed directly
                logger.warning(
                    "idx_short_constraint: short leg for %s cannot be fully expressed "
                    "(IDX no naked short-selling). Using underweight instead.",
                    x_name,
                )
            elif z > self._entry_z:
                signals.append(
                    PairSignal(
                        symbol_long=str(x_name),
                        symbol_short=str(y_name),
                        z_score=float(z),
                        hedge_ratio=float(hr),
                        action="ENTER_SHORT",
                        kelly_fraction=kelly,
                    )
                )
                logger.warning(
                    "idx_short_constraint: short leg for %s cannot be fully expressed "
                    "(IDX no naked short-selling). Using underweight instead.",
                    y_name,
                )
            elif abs(z) < self._exit_z:
                signals.append(
                    PairSignal(
                        symbol_long=str(y_name),
                        symbol_short=str(x_name),
                        z_score=float(z),
                        hedge_ratio=float(hr),
                        action="EXIT",
                        kelly_fraction=0.0,
                    )
                )

        return signals
