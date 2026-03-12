"""Dynamic IC-weighted signal combination for IDX.

Combines LightGBM alpha scores and LSTM momentum decomposition
using rolling Information Coefficient (IC) as dynamic weights.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from scipy.stats import spearmanr


class IDXSignalCombiner:
    """Combines multiple alpha signals using dynamic IC weighting.

    Each model's signal is weighted by its recent IC (Spearman rank
    correlation with realised returns) over a rolling window.
    Models with negative IC are given zero weight.

    Parameters
    ----------
    ic_lookback : int
        Number of cross-sections (dates) for rolling IC computation.
    min_ic_weight : float
        Minimum IC to receive positive weight (models below this get 0).
    decay_factor : float
        Exponential decay for IC weighting (1.0 = equal weight to all lookback).
    """

    def __init__(
        self,
        ic_lookback: int = 63,
        min_ic_weight: float = 0.0,
        decay_factor: float = 0.94,
    ) -> None:
        self._ic_lookback = ic_lookback
        self._min_ic_weight = min_ic_weight
        self._decay_factor = decay_factor
        self._model_ics: dict[str, list[float]] = {}
        self._current_weights: dict[str, float] = {}

    @property
    def current_weights(self) -> dict[str, float]:
        """Current model weights."""
        return dict(self._current_weights)

    @property
    def model_ics(self) -> dict[str, list[float]]:
        """Historical IC values per model."""
        return {k: list(v) for k, v in self._model_ics.items()}

    def combine(
        self,
        signals: dict[str, pd.Series],
        realised_returns: pd.Series | None = None,
    ) -> pd.Series:
        """Combine multiple signal series using IC weights.

        Parameters
        ----------
        signals : dict[str, Series]
            Model name → alpha signal Series (same index).
        realised_returns : Series, optional
            Realised returns for IC computation. If provided, updates
            rolling IC estimates and recomputes weights.

        Returns
        -------
        Series
            Combined signal.
        """
        if not signals:
            raise ValueError("No signals to combine.")

        model_names = list(signals.keys())

        # Update ICs if realised returns provided
        if realised_returns is not None:
            self._update_ics(signals, realised_returns)
            self._recompute_weights(model_names)
        elif not self._current_weights:
            # Equal weights if no IC history
            w = 1.0 / len(model_names)
            self._current_weights = {name: w for name in model_names}

        # Combine signals
        combined = pd.Series(0.0, index=next(iter(signals.values())).index)
        total_weight = sum(self._current_weights.get(name, 0.0) for name in model_names)

        if total_weight <= 0:
            # Fallback to equal weights
            total_weight = len(model_names)
            weights = {name: 1.0 / total_weight for name in model_names}
        else:
            weights = {
                name: self._current_weights.get(name, 0.0) / total_weight
                for name in model_names
            }

        for name, signal in signals.items():
            combined += signal * weights.get(name, 0.0)

        return combined.rename("combined_alpha")

    def combine_with_metadata(
        self,
        signals: dict[str, pd.Series],
        realised_returns: pd.Series | None = None,
    ) -> dict[str, object]:
        """Combine signals and return metadata about the combination.

        Returns dict with:
        - combined_signal: Series
        - weights: dict[str, float]
        - model_ics: dict[str, float] (latest IC per model)
        - aggregate_ic: float
        """
        combined = self.combine(signals, realised_returns)

        latest_ics = {}
        for name in signals:
            ic_history = self._model_ics.get(name, [])
            latest_ics[name] = ic_history[-1] if ic_history else 0.0

        # Compute aggregate IC if realised returns available
        aggregate_ic = 0.0
        if realised_returns is not None:
            common = combined.index.intersection(realised_returns.index)
            if len(common) > 2:
                ic, _ = spearmanr(
                    combined.loc[common],
                    realised_returns.loc[common],
                )
                if not np.isnan(ic):
                    aggregate_ic = float(ic)

        return {
            "combined_signal": combined,
            "weights": dict(self._current_weights),
            "model_ics": latest_ics,
            "aggregate_ic": aggregate_ic,
        }

    def _update_ics(
        self,
        signals: dict[str, pd.Series],
        realised_returns: pd.Series,
    ) -> None:
        """Update rolling IC estimates for each model."""
        for name, signal in signals.items():
            if name not in self._model_ics:
                self._model_ics[name] = []

            common = signal.index.intersection(realised_returns.index)
            if len(common) < 3:
                continue

            # Compute cross-sectional IC if MultiIndex
            if isinstance(common, pd.MultiIndex):
                dates = common.get_level_values(0).unique()
                for dt in dates:
                    try:
                        sig_cs = signal.loc[dt]
                        ret_cs = realised_returns.loc[dt]
                        if len(sig_cs) < 3:
                            continue
                        ic, _ = spearmanr(sig_cs, ret_cs)
                        if not np.isnan(ic):
                            self._model_ics[name].append(float(ic))
                    except (KeyError, TypeError):
                        continue
            else:
                ic, _ = spearmanr(signal.loc[common], realised_returns.loc[common])
                if not np.isnan(ic):
                    self._model_ics[name].append(float(ic))

            # Keep only lookback window
            if len(self._model_ics[name]) > self._ic_lookback:
                self._model_ics[name] = self._model_ics[name][-self._ic_lookback:]

    def _recompute_weights(self, model_names: list[str]) -> None:
        """Recompute model weights from rolling IC with exponential decay."""
        raw_weights: dict[str, float] = {}

        for name in model_names:
            ics = self._model_ics.get(name, [])
            if not ics:
                raw_weights[name] = 0.0
                continue

            # Apply exponential decay to ICs
            n = len(ics)
            decay_weights = np.array([
                self._decay_factor ** (n - 1 - i) for i in range(n)
            ])
            decay_weights /= decay_weights.sum()
            weighted_ic = float(np.dot(ics, decay_weights))

            # Zero out negative ICs
            raw_weights[name] = max(weighted_ic - self._min_ic_weight, 0.0)

        # Normalise
        total = sum(raw_weights.values())
        if total > 0:
            self._current_weights = {
                name: w / total for name, w in raw_weights.items()
            }
        else:
            # Equal weights as fallback
            w = 1.0 / len(model_names) if model_names else 0.0
            self._current_weights = {name: w for name in model_names}

    def get_ic_summary(self) -> pd.DataFrame:
        """Return IC summary statistics per model.

        Returns DataFrame with columns: mean_ic, std_ic, icir, n_observations.
        """
        rows = []
        for name, ics in self._model_ics.items():
            if ics:
                mean_ic = float(np.mean(ics))
                std_ic = float(np.std(ics))
                icir = mean_ic / std_ic if std_ic > 0 else 0.0
                rows.append({
                    "model": name,
                    "mean_ic": mean_ic,
                    "std_ic": std_ic,
                    "icir": icir,
                    "n_observations": len(ics),
                    "weight": self._current_weights.get(name, 0.0),
                })

        if not rows:
            return pd.DataFrame(columns=["model", "mean_ic", "std_ic", "icir", "n_observations", "weight"])

        return pd.DataFrame(rows).set_index("model")
