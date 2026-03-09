"""Engle-Granger cointegration pairs trading strategy with Kalman filter.

Identifies cointegrated IDX equity pairs using the Engle-Granger two-step
procedure, then tracks the hedge ratio dynamically with a Kalman filter.
Trades when the spread z-score breaches configurable thresholds.

References:
    Engle & Granger (1987) — *Co-Integration and Error Correction*.
    Gatev, Goetzmann & Rouwenhorst (2006) — *Pairs Trading*.

Usage::

    strategy = IDXPairsCointegrationStrategy()
    signals = await strategy.generate_signals(market_data, as_of_date)
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

import numpy as np
import pandas as pd
from statsmodels.tsa.stattools import coint

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

# ── Default pairs universe (banking & telco) ────────────────────────────────

_DEFAULT_PAIR_CANDIDATES: list[tuple[str, str]] = [
    ("BBCA", "BBRI"),
    ("BBRI", "BMRI"),
    ("BBNI", "BMRI"),
    ("TLKM", "EXCL"),
    ("ICBP", "INDF"),
    ("SMGR", "INTP"),
    ("ADRO", "ITMG"),
    ("ASII", "UNTR"),
]


class _KalmanHedgeRatio:
    """Online Kalman filter for dynamic hedge ratio estimation.

    State: hedge ratio (beta).  Observation: y_t = beta * x_t + e_t.

    Args:
        delta: State transition variance (controls adaptation speed).
        ve: Observation noise variance.
    """

    def __init__(self, delta: float = 1e-4, ve: float = 1e-3) -> None:
        self.delta = delta
        self.ve = ve
        self.beta: float = 0.0
        self._R: float = 1.0

    def update(self, x: float, y: float) -> float:
        """Incorporate a new observation and return updated hedge ratio.

        Args:
            x: Independent variable price.
            y: Dependent variable price.

        Returns:
            Updated hedge ratio estimate.
        """
        R_prior = self._R + self.delta
        K = R_prior * x / (x * R_prior * x + self.ve)
        self.beta += K * (y - self.beta * x)
        self._R = (1.0 - K * x) * R_prior
        return self.beta


class IDXPairsCointegrationStrategy(BaseStrategyInterface):
    """Engle-Granger cointegration pairs trading with Kalman hedge ratio.

    Args:
        pair_candidates: List of (symbol_a, symbol_b) tuples to test.
        formation_days: Look-back window for cointegration test.
        zscore_entry: Z-score threshold for entry (default 2.0).
        zscore_exit: Z-score threshold for exit (default 0.5).
        coint_pvalue: Maximum p-value for Engle-Granger test.
        strategy_id: Unique strategy identifier.
    """

    def __init__(
        self,
        pair_candidates: list[tuple[str, str]] | None = None,
        formation_days: int = 252,
        zscore_entry: float = 2.0,
        zscore_exit: float = 0.5,
        coint_pvalue: float = 0.05,
        strategy_id: str = "idx_pairs_coint",
    ) -> None:
        self._pairs = pair_candidates or list(_DEFAULT_PAIR_CANDIDATES)
        self._formation_days = formation_days
        self._zscore_entry = zscore_entry
        self._zscore_exit = zscore_exit
        self._coint_pvalue = coint_pvalue
        self._strategy_id = strategy_id
        self._kalman_filters: dict[tuple[str, str], _KalmanHedgeRatio] = {}
        self._bar_buffer: dict[str, list[BarData]] = {}

        all_symbols = {s for pair in self._pairs for s in pair}
        for sym in all_symbols:
            self._bar_buffer[sym] = []

        logger.info(
            "pairs_strategy_initialised",
            strategy_id=self._strategy_id,
            num_pairs=len(self._pairs),
        )

    def get_parameters(self) -> StrategyParameters:
        universe = list({s for pair in self._pairs for s in pair})
        return StrategyParameters(
            name="IDX Pairs Cointegration (Engle-Granger + Kalman)",
            version="1.0.0",
            universe=universe,
            lookback_days=self._formation_days,
            rebalance_frequency="daily",
            custom={
                "zscore_entry": self._zscore_entry,
                "zscore_exit": self._zscore_exit,
                "coint_pvalue": self._coint_pvalue,
            },
        )

    async def generate_signals(
        self, market_data: pd.DataFrame, as_of_date: datetime
    ) -> list[StrategySignal]:
        logger.info("pairs_signal_generation_start", as_of_date=as_of_date.isoformat())
        try:
            return self._compute_pairs_signals(market_data, as_of_date)
        except (KeyError, ValueError) as exc:
            logger.error("pairs_signal_generation_failed", error=str(exc))
            return []

    async def on_bar(self, bar: BarData) -> list[StrategySignal]:
        if bar.symbol in self._bar_buffer:
            self._bar_buffer[bar.symbol].append(bar)
        return []

    async def on_tick(self, tick: TickData) -> list[StrategySignal]:
        return []

    def _compute_pairs_signals(
        self, market_data: pd.DataFrame, as_of_date: datetime
    ) -> list[StrategySignal]:
        if isinstance(market_data.index, pd.MultiIndex):
            close = market_data["close"].unstack(level="symbol")
        else:
            close = market_data.pivot(columns="symbol", values="close")

        close = close.loc[close.index <= as_of_date].sort_index()
        close = close.iloc[-self._formation_days:]
        signals: list[StrategySignal] = []

        for sym_a, sym_b in self._pairs:
            if sym_a not in close.columns or sym_b not in close.columns:
                continue

            series_a = close[sym_a].dropna()
            series_b = close[sym_b].dropna()
            common_idx = series_a.index.intersection(series_b.index)
            if len(common_idx) < 60:
                continue

            sa, sb = series_a.loc[common_idx], series_b.loc[common_idx]

            _, pvalue, _ = coint(sa.values, sb.values)
            if pvalue > self._coint_pvalue:
                continue

            pair_key = (sym_a, sym_b)
            if pair_key not in self._kalman_filters:
                self._kalman_filters[pair_key] = _KalmanHedgeRatio()

            kf = self._kalman_filters[pair_key]
            for xa, xb in zip(sa.values, sb.values):
                kf.update(xa, xb)

            spread = sb.values - kf.beta * sa.values
            zscore = (spread[-1] - np.mean(spread)) / (np.std(spread) + 1e-9)

            if abs(zscore) >= self._zscore_entry:
                direction_a = SignalDirection.LONG if zscore < 0 else SignalDirection.SHORT
                direction_b = SignalDirection.SHORT if zscore < 0 else SignalDirection.LONG
                for sym, direction in [(sym_a, direction_a), (sym_b, direction_b)]:
                    signals.append(
                        StrategySignal(
                            symbol=sym,
                            direction=direction,
                            target_weight=0.05,
                            confidence=min(abs(zscore) / 4.0, 1.0),
                            strategy_id=self._strategy_id,
                            generated_at=as_of_date,
                            metadata={
                                "pair": f"{sym_a}/{sym_b}",
                                "zscore": round(float(zscore), 4),
                                "hedge_ratio": round(kf.beta, 6),
                                "coint_pvalue": round(float(pvalue), 4),
                            },
                        )
                    )

        logger.info("pairs_signal_generation_complete", signal_count=len(signals))
        return signals
