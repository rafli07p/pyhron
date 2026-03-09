"""Engle-Granger cointegration pairs trading with Kalman filter hedge ratio.

Tests cointegration on pre-defined IDX pairs (e.g. BBCA/BBRI, TLKM/EXCL),
estimates the hedge ratio via a Kalman filter, and trades the spread when it
deviates beyond a z-score threshold.

Usage::

    strategy = IDXPairsCointegrationStrategy()
    signals = await strategy.generate_signals(market_data, as_of_date)
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any

import numpy as np
import pandas as pd

from shared.structured_json_logger import get_logger
from strategy_engine.base_strategy_interface import (
    BaseStrategyInterface,
    BarData,
    SignalDirection,
    StrategyParameters,
    StrategySignal,
    TickData,
)

logger = get_logger(__name__)

# ── Default pairs ────────────────────────────────────────────────────────────

_DEFAULT_PAIRS: list[tuple[str, str]] = [
    ("BBCA", "BBRI"),
    ("BBCA", "BMRI"),
    ("BBRI", "BMRI"),
    ("TLKM", "EXCL"),
    ("TLKM", "ISAT"),
    ("ADRO", "ITMG"),
    ("ADRO", "PTBA"),
    ("ICBP", "INDF"),
    ("SMGR", "INTP"),
    ("TOWR", "TBIG"),
]


@dataclass
class KalmanState:
    """State for a single Kalman filter tracking the hedge ratio.

    Attributes:
        beta: Current hedge ratio estimate.
        P: Estimate covariance.
        Q: Process noise variance.
        R: Observation noise variance.
    """

    beta: float
    P: float
    Q: float
    R: float


@dataclass
class PairState:
    """Tracking state for a single pair.

    Attributes:
        leg_a: Symbol of the first leg.
        leg_b: Symbol of the second leg.
        kalman: Kalman filter state for the hedge ratio.
        spread_mean: Running mean of the spread.
        spread_std: Running standard deviation of the spread.
        position: Current position: 0 = flat, 1 = long spread, -1 = short spread.
    """

    leg_a: str
    leg_b: str
    kalman: KalmanState
    spread_mean: float = 0.0
    spread_std: float = 1.0
    position: int = 0


class IDXPairsCointegrationStrategy(BaseStrategyInterface):
    """Engle-Granger cointegration pairs trading with Kalman filter hedge ratio.

    The strategy:
        1. Tests each pair for cointegration using the Engle-Granger ADF test.
        2. Estimates the time-varying hedge ratio with a Kalman filter.
        3. Computes the spread: ``price_A - beta * price_B``.
        4. Enters when the spread z-score exceeds ``entry_z`` (default 2.0).
        5. Exits when the spread reverts within ``exit_z`` (default 0.5).

    Args:
        pairs: List of (symbol_a, symbol_b) tuples.
        lookback_days: Window for spread statistics (default 60).
        entry_z: Z-score threshold for entry (default 2.0).
        exit_z: Z-score threshold for exit (default 0.5).
        kalman_q: Kalman process noise (default 1e-5).
        kalman_r: Kalman observation noise (default 1e-3).
        coint_pvalue: Maximum ADF p-value to accept cointegration (default 0.05).
        weight_per_pair: Portfolio weight per pair trade (default 0.05).
        strategy_id: Unique identifier for this strategy instance.
    """

    def __init__(
        self,
        pairs: list[tuple[str, str]] | None = None,
        lookback_days: int = 60,
        entry_z: float = 2.0,
        exit_z: float = 0.5,
        kalman_q: float = 1e-5,
        kalman_r: float = 1e-3,
        coint_pvalue: float = 0.05,
        weight_per_pair: float = 0.05,
        strategy_id: str = "idx_pairs_cointegration",
    ) -> None:
        self._pairs = pairs or list(_DEFAULT_PAIRS)
        self._lookback_days = lookback_days
        self._entry_z = entry_z
        self._exit_z = exit_z
        self._kalman_q = kalman_q
        self._kalman_r = kalman_r
        self._coint_pvalue = coint_pvalue
        self._weight = weight_per_pair
        self._strategy_id = strategy_id

        # Build universe from pairs
        symbols: set[str] = set()
        for a, b in self._pairs:
            symbols.add(a)
            symbols.add(b)
        self._universe = sorted(symbols)

        # Pair states
        self._pair_states: dict[str, PairState] = {}
        for a, b in self._pairs:
            key = f"{a}/{b}"
            self._pair_states[key] = PairState(
                leg_a=a,
                leg_b=b,
                kalman=KalmanState(beta=1.0, P=1.0, Q=kalman_q, R=kalman_r),
            )

        logger.info(
            "pairs_strategy_initialised",
            strategy_id=self._strategy_id,
            pair_count=len(self._pairs),
            entry_z=self._entry_z,
            exit_z=self._exit_z,
        )

    # ── Interface implementation ─────────────────────────────────────────

    def get_parameters(self) -> StrategyParameters:
        """Return current strategy parameters.

        Returns:
            StrategyParameters with pairs-trading-specific configuration.
        """
        return StrategyParameters(
            name="IDX Pairs Cointegration (Engle-Granger + Kalman)",
            version="1.0.0",
            universe=list(self._universe),
            lookback_days=self._lookback_days + 60,
            rebalance_frequency="daily",
            custom={
                "pairs": [f"{a}/{b}" for a, b in self._pairs],
                "entry_z": self._entry_z,
                "exit_z": self._exit_z,
                "coint_pvalue": self._coint_pvalue,
                "kalman_q": self._kalman_q,
                "kalman_r": self._kalman_r,
            },
        )

    async def generate_signals(
        self,
        market_data: pd.DataFrame,
        as_of_date: datetime,
    ) -> list[StrategySignal]:
        """Generate pairs-trading signals.

        Args:
            market_data: DataFrame with multi-index ``(date, symbol)`` and
                column ``close``.
            as_of_date: Evaluation date.

        Returns:
            List of LONG, SHORT, and CLOSE signals for pair legs.
        """
        logger.info("pairs_signal_generation_start", as_of_date=as_of_date.isoformat())

        try:
            signals = self._compute_pairs_signals(market_data, as_of_date)
            logger.info(
                "pairs_signal_generation_complete",
                as_of_date=as_of_date.isoformat(),
                signal_count=len(signals),
            )
            return signals
        except (KeyError, ValueError) as exc:
            logger.error("pairs_signal_generation_failed", error=str(exc))
            return []

    async def on_bar(self, bar: BarData) -> list[StrategySignal]:
        """No-op for daily pair rebalance strategy.

        Args:
            bar: A single OHLCV bar.

        Returns:
            Empty list.
        """
        return []

    async def on_tick(self, tick: TickData) -> list[StrategySignal]:
        """No-op for daily pair rebalance strategy.

        Args:
            tick: A single tick event.

        Returns:
            Empty list.
        """
        return []

    # ── Kalman Filter ────────────────────────────────────────────────────

    def _kalman_update(
        self,
        state: KalmanState,
        price_a: float,
        price_b: float,
    ) -> tuple[float, float]:
        """Run one step of the Kalman filter to estimate hedge ratio.

        The observation model is: ``price_A = beta * price_B + epsilon``.

        Args:
            state: Current Kalman filter state.
            price_a: Price of the dependent leg.
            price_b: Price of the independent leg.

        Returns:
            Tuple of (updated_beta, spread_residual).
        """
        # Predict
        beta_pred = state.beta
        P_pred = state.P + state.Q

        # Update
        y = price_a - beta_pred * price_b  # innovation (spread)
        S = P_pred * price_b * price_b + state.R  # innovation covariance
        K = P_pred * price_b / S  # Kalman gain

        state.beta = beta_pred + K * y
        state.P = (1.0 - K * price_b) * P_pred

        return state.beta, y

    # ── Cointegration Test ───────────────────────────────────────────────

    @staticmethod
    def _engle_granger_adf_test(
        series_a: pd.Series,
        series_b: pd.Series,
    ) -> tuple[bool, float, float]:
        """Simplified Engle-Granger cointegration test.

        Runs OLS regression of A on B, then applies an ADF test on the
        residuals.  Uses the Dickey-Fuller critical values approximation.

        Args:
            series_a: Price series of leg A (aligned with B).
            series_b: Price series of leg B (aligned with A).

        Returns:
            Tuple of (is_cointegrated, ols_beta, approx_pvalue).
        """
        # OLS regression: A = beta * B + alpha + epsilon
        b_mean = series_b.mean()
        a_mean = series_a.mean()
        b_demeaned = series_b - b_mean

        cov_ab = ((series_a - a_mean) * b_demeaned).mean()
        var_b = (b_demeaned ** 2).mean()

        if var_b < 1e-12:
            return False, 0.0, 1.0

        beta = cov_ab / var_b
        alpha = a_mean - beta * b_mean
        residuals = series_a - (beta * series_b + alpha)

        # ADF test on residuals (simplified: check first-order autocorrelation)
        n = len(residuals)
        if n < 30:
            return False, float(beta), 1.0

        diff_resid = residuals.diff().dropna()
        lagged_resid = residuals.shift(1).dropna()

        # Align
        diff_resid = diff_resid.iloc[:len(lagged_resid)]
        lagged_resid = lagged_resid.iloc[:len(diff_resid)]

        # OLS: diff_resid = gamma * lagged_resid + error
        lr_mean = lagged_resid.mean()
        lr_demeaned = lagged_resid - lr_mean
        var_lr = (lr_demeaned ** 2).mean()

        if var_lr < 1e-12:
            return False, float(beta), 1.0

        gamma = ((diff_resid - diff_resid.mean()) * lr_demeaned).mean() / var_lr
        se_gamma_residuals = diff_resid - (gamma * lagged_resid + (diff_resid.mean() - gamma * lr_mean))
        se_gamma = float(np.sqrt((se_gamma_residuals ** 2).mean() / (var_lr * n)))

        if se_gamma < 1e-12:
            return False, float(beta), 1.0

        t_stat = gamma / se_gamma

        # Approximate p-value using ADF critical values for n > 100
        # Critical values: 1% = -3.43, 5% = -2.86, 10% = -2.57
        if t_stat < -3.43:
            approx_p = 0.01
        elif t_stat < -2.86:
            approx_p = 0.05
        elif t_stat < -2.57:
            approx_p = 0.10
        else:
            approx_p = 0.50

        is_coint = approx_p <= 0.05
        return is_coint, float(beta), approx_p

    # ── Signal Computation ───────────────────────────────────────────────

    def _compute_pairs_signals(
        self,
        market_data: pd.DataFrame,
        as_of_date: datetime,
    ) -> list[StrategySignal]:
        """Core pairs-trading signal computation.

        Steps:
            1. Pivot to date x symbol close matrix.
            2. For each pair, test cointegration over the look-back window.
            3. Update the Kalman-filter hedge ratio.
            4. Compute spread z-score.
            5. Generate entry/exit signals based on z-score thresholds.

        Args:
            market_data: Multi-index (date, symbol) DataFrame with ``close``.
            as_of_date: Evaluation date.

        Returns:
            List of trading signals.
        """
        # Pivot to date x symbol close matrix
        if isinstance(market_data.index, pd.MultiIndex):
            close_prices = market_data["close"].unstack(level="symbol")
        else:
            close_prices = market_data.pivot(columns="symbol", values="close")

        close_prices = close_prices.loc[close_prices.index <= as_of_date].sort_index()

        signals: list[StrategySignal] = []

        for pair_key, pair_state in self._pair_states.items():
            a, b = pair_state.leg_a, pair_state.leg_b

            if a not in close_prices.columns or b not in close_prices.columns:
                continue

            # Get aligned price series
            pair_data = close_prices[[a, b]].dropna()
            if len(pair_data) < self._lookback_days:
                logger.debug(
                    "pairs_insufficient_data",
                    pair=pair_key,
                    available=len(pair_data),
                    required=self._lookback_days,
                )
                continue

            lookback_data = pair_data.iloc[-self._lookback_days:]
            series_a = lookback_data[a]
            series_b = lookback_data[b]

            # Test cointegration
            is_coint, ols_beta, pvalue = self._engle_granger_adf_test(series_a, series_b)

            if not is_coint:
                # If not cointegrated and we have a position, close it
                if pair_state.position != 0:
                    signals.extend(
                        self._create_close_signals(pair_state, as_of_date, "cointegration_breakdown")
                    )
                    pair_state.position = 0
                continue

            # Update Kalman filter with latest prices
            price_a = float(series_a.iloc[-1])
            price_b = float(series_b.iloc[-1])
            beta, spread = self._kalman_update(pair_state.kalman, price_a, price_b)

            # Compute spread series using Kalman beta
            spread_series = series_a.values - beta * series_b.values
            pair_state.spread_mean = float(np.mean(spread_series))
            pair_state.spread_std = float(np.std(spread_series, ddof=1))

            if pair_state.spread_std < 1e-8:
                continue

            z_score = (spread - pair_state.spread_mean) / pair_state.spread_std

            logger.debug(
                "pairs_z_score",
                pair=pair_key,
                z_score=round(z_score, 4),
                beta=round(beta, 4),
                spread=round(spread, 4),
            )

            # Generate signals based on z-score
            if pair_state.position == 0:
                # No position — check for entry
                if z_score < -self._entry_z:
                    # Spread is too low: long A, short B
                    signals.extend(
                        self._create_entry_signals(
                            pair_state, as_of_date, z_score, beta,
                            long_a=True,
                        )
                    )
                    pair_state.position = 1
                elif z_score > self._entry_z:
                    # Spread is too high: short A, long B
                    signals.extend(
                        self._create_entry_signals(
                            pair_state, as_of_date, z_score, beta,
                            long_a=False,
                        )
                    )
                    pair_state.position = -1
            else:
                # Have position — check for exit
                if abs(z_score) < self._exit_z:
                    signals.extend(
                        self._create_close_signals(pair_state, as_of_date, "mean_reversion")
                    )
                    pair_state.position = 0

        return signals

    def _create_entry_signals(
        self,
        pair_state: PairState,
        as_of_date: datetime,
        z_score: float,
        beta: float,
        long_a: bool,
    ) -> list[StrategySignal]:
        """Create entry signals for a pair trade.

        Args:
            pair_state: State of the pair.
            as_of_date: Signal timestamp.
            z_score: Current spread z-score.
            beta: Current hedge ratio.
            long_a: If True, go long A and short B; otherwise the reverse.

        Returns:
            Two signals — one for each leg.
        """
        confidence = min(0.95, abs(z_score) / (self._entry_z * 2))

        dir_a = SignalDirection.LONG if long_a else SignalDirection.SHORT
        dir_b = SignalDirection.SHORT if long_a else SignalDirection.LONG

        meta = {
            "pair": f"{pair_state.leg_a}/{pair_state.leg_b}",
            "z_score": round(z_score, 4),
            "hedge_ratio": round(beta, 6),
            "entry_reason": "spread_divergence",
        }

        return [
            StrategySignal(
                symbol=pair_state.leg_a,
                direction=dir_a,
                target_weight=self._weight,
                confidence=round(confidence, 4),
                strategy_id=self._strategy_id,
                generated_at=as_of_date,
                metadata={**meta, "leg": "A"},
            ),
            StrategySignal(
                symbol=pair_state.leg_b,
                direction=dir_b,
                target_weight=self._weight * beta,
                confidence=round(confidence, 4),
                strategy_id=self._strategy_id,
                generated_at=as_of_date,
                metadata={**meta, "leg": "B"},
            ),
        ]

    def _create_close_signals(
        self,
        pair_state: PairState,
        as_of_date: datetime,
        reason: str,
    ) -> list[StrategySignal]:
        """Create close signals for both legs of a pair.

        Args:
            pair_state: State of the pair.
            as_of_date: Signal timestamp.
            reason: Reason for closing the position.

        Returns:
            Two CLOSE signals — one for each leg.
        """
        meta = {
            "pair": f"{pair_state.leg_a}/{pair_state.leg_b}",
            "exit_reason": reason,
        }

        return [
            StrategySignal(
                symbol=pair_state.leg_a,
                direction=SignalDirection.CLOSE,
                target_weight=0.0,
                confidence=0.9,
                strategy_id=self._strategy_id,
                generated_at=as_of_date,
                metadata={**meta, "leg": "A"},
            ),
            StrategySignal(
                symbol=pair_state.leg_b,
                direction=SignalDirection.CLOSE,
                target_weight=0.0,
                confidence=0.9,
                strategy_id=self._strategy_id,
                generated_at=as_of_date,
                metadata={**meta, "leg": "B"},
            ),
        ]
