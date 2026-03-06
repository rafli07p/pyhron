"""Enthropy Signal Generation.

Combines multiple alpha models into composite trading signals.
Handles signal normalisation, ranking across symbols, and filtering
by minimum thresholds.  Optionally integrates with the research
service's factor engine for factor-based scoring.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Optional

import numpy as np
import pandas as pd
import structlog

from strategies.alpha_models import AlphaSignal, BaseAlphaModel

logger = structlog.stdlib.get_logger(__name__)


# ---------------------------------------------------------------------------
# Composite signal
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class CompositeSignal:
    """Weighted combination of multiple alpha signals for one symbol."""

    symbol: str
    composite_score: float  # [-1, +1]
    rank: Optional[int] = None
    component_signals: dict[str, float] = field(default_factory=dict)
    factor_scores: dict[str, float] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=lambda: datetime.now(tz=timezone.utc))


# ---------------------------------------------------------------------------
# Signal generator
# ---------------------------------------------------------------------------

class SignalGenerator:
    """Combine multiple alpha models with configurable weights.

    The generator runs each registered alpha model on the provided
    data, produces weighted composite signals, normalises them, and
    ranks symbols by signal strength.

    Parameters
    ----------
    models:
        List of ``(alpha_model, weight)`` tuples.
    min_signal_threshold:
        Absolute signal value below which the signal is filtered out
        (default 0.05).
    use_factor_engine:
        When ``True``, fetch factor scores from the research factor
        engine and blend them into the composite (default ``False``).
    factor_weight:
        Weight given to the factor engine score when blending
        (default 0.3).
    """

    def __init__(
        self,
        models: Optional[list[tuple[BaseAlphaModel, float]]] = None,
        min_signal_threshold: float = 0.05,
        use_factor_engine: bool = False,
        factor_weight: float = 0.3,
    ) -> None:
        self._models: list[tuple[BaseAlphaModel, float]] = models or []
        self.min_signal_threshold = min_signal_threshold
        self.use_factor_engine = use_factor_engine
        self.factor_weight = factor_weight

    # -- model management ---------------------------------------------------

    def add_model(self, model: BaseAlphaModel, weight: float = 1.0) -> None:
        """Register an alpha model with a weight."""
        self._models.append((model, weight))
        logger.info("model_added", model=model.name, weight=weight, total=len(self._models))

    def remove_model(self, model_name: str) -> None:
        """Remove a model by name."""
        self._models = [(m, w) for m, w in self._models if m.name != model_name]

    @property
    def model_names(self) -> list[str]:
        return [m.name for m, _ in self._models]

    # -- signal generation ---------------------------------------------------

    def generate_signals(
        self,
        symbols: list[str],
        data: dict[str, pd.DataFrame],
    ) -> list[CompositeSignal]:
        """Generate composite signals for a universe of symbols.

        Parameters
        ----------
        symbols:
            List of instrument symbols to score.
        data:
            Mapping of symbol -> OHLCV DataFrame.

        Returns
        -------
        list[CompositeSignal]
            Composite signals sorted by absolute signal strength
            (strongest first), with ranks assigned.
        """
        raw_signals: list[CompositeSignal] = []

        for symbol in symbols:
            df = data.get(symbol)
            if df is None or df.empty:
                logger.warning("no_data_for_symbol", symbol=symbol)
                continue

            components = self._run_models(symbol, df)
            composite = self.combine_signals(components)

            # Factor engine blending
            factor_scores: dict[str, float] = {}
            if self.use_factor_engine:
                factor_scores = self._fetch_factor_scores(symbol, df)
                if factor_scores:
                    factor_composite = float(np.mean(list(factor_scores.values())))
                    composite = (
                        (1 - self.factor_weight) * composite
                        + self.factor_weight * factor_composite
                    )

            composite = float(np.clip(composite, -1.0, 1.0))

            raw_signals.append(CompositeSignal(
                symbol=symbol,
                composite_score=composite,
                component_signals={name: val for name, val in components},
                factor_scores=factor_scores,
            ))

        # Filter and rank
        filtered = self.filter_signals(raw_signals)
        ranked = self._rank_signals(filtered)
        return ranked

    def _run_models(self, symbol: str, data: pd.DataFrame) -> list[tuple[str, float]]:
        """Run all registered alpha models and return (name, signal) pairs."""
        results: list[tuple[str, float]] = []
        for model, _weight in self._models:
            try:
                sig = model.generate_signal(data)
                results.append((model.name, float(sig)))
            except Exception:
                logger.exception("alpha_model_error", model=model.name, symbol=symbol)
                results.append((model.name, 0.0))
        return results

    def combine_signals(self, components: list[tuple[str, float]]) -> float:
        """Weighted combination of component signals.

        Parameters
        ----------
        components:
            List of (model_name, signal_value) tuples.

        Returns
        -------
        float
            Weighted average signal in [-1, +1].
        """
        if not components or not self._models:
            return 0.0

        weight_map = {m.name: w for m, w in self._models}
        total_weight = 0.0
        weighted_sum = 0.0

        for name, value in components:
            w = weight_map.get(name, 1.0)
            weighted_sum += value * w
            total_weight += abs(w)

        if total_weight < 1e-12:
            return 0.0

        return weighted_sum / total_weight

    def filter_signals(
        self,
        signals: list[CompositeSignal],
        threshold: Optional[float] = None,
    ) -> list[CompositeSignal]:
        """Remove signals below the minimum absolute threshold."""
        t = threshold if threshold is not None else self.min_signal_threshold
        return [s for s in signals if abs(s.composite_score) >= t]

    def _rank_signals(self, signals: list[CompositeSignal]) -> list[CompositeSignal]:
        """Sort signals by absolute strength and assign ranks."""
        sorted_signals = sorted(signals, key=lambda s: abs(s.composite_score), reverse=True)
        ranked: list[CompositeSignal] = []
        for i, sig in enumerate(sorted_signals, start=1):
            ranked.append(CompositeSignal(
                symbol=sig.symbol,
                composite_score=sig.composite_score,
                rank=i,
                component_signals=sig.component_signals,
                factor_scores=sig.factor_scores,
                timestamp=sig.timestamp,
            ))
        return ranked

    @staticmethod
    def normalize_signals(signals: list[CompositeSignal]) -> list[CompositeSignal]:
        """Cross-sectional normalisation: z-score across all symbols.

        Useful for dollar-neutral strategies that care about relative
        signal ranking rather than absolute levels.
        """
        if len(signals) < 2:
            return signals

        scores = np.array([s.composite_score for s in signals])
        mean = float(np.mean(scores))
        std = float(np.std(scores, ddof=1))
        if std < 1e-12:
            return signals

        normalised: list[CompositeSignal] = []
        for sig in signals:
            z = (sig.composite_score - mean) / std
            z_clipped = float(np.clip(np.tanh(z / 3.0), -1.0, 1.0))
            normalised.append(CompositeSignal(
                symbol=sig.symbol,
                composite_score=z_clipped,
                rank=sig.rank,
                component_signals=sig.component_signals,
                factor_scores=sig.factor_scores,
                timestamp=sig.timestamp,
            ))
        return normalised

    # -- factor engine integration ------------------------------------------

    def _fetch_factor_scores(self, symbol: str, data: pd.DataFrame) -> dict[str, float]:
        """Compute basic factor scores locally.

        In production this would call the research factor_engine
        service; here we compute lightweight proxies.
        """
        try:
            close = data["close"].astype(float)
            volume = data["volume"].astype(float)

            factors: dict[str, float] = {}

            # Momentum factor
            if len(close) >= 252:
                factors["momentum_12m"] = float(close.iloc[-1] / close.iloc[-252] - 1)
            elif len(close) >= 20:
                factors["momentum_1m"] = float(close.iloc[-1] / close.iloc[-20] - 1)

            # Volatility factor (lower vol = higher score)
            if len(close) >= 20:
                vol = float(close.pct_change().rolling(20).std().iloc[-1])
                factors["low_volatility"] = float(np.tanh(-vol * 10))

            # Volume factor (liquidity)
            if len(volume) >= 20:
                avg_vol = float(volume.rolling(20).mean().iloc[-1])
                factors["liquidity"] = float(np.tanh(avg_vol / 1e6))

            # Value factor (simple: 52-week price-to-high ratio inverted)
            if len(close) >= 252:
                high_52w = float(close.rolling(252).max().iloc[-1])
                if high_52w > 0:
                    factors["value"] = 1.0 - float(close.iloc[-1]) / high_52w

            return factors
        except Exception:
            logger.exception("factor_score_error", symbol=symbol)
            return {}


__all__ = [
    "CompositeSignal",
    "SignalGenerator",
]
