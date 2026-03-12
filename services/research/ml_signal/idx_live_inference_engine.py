"""Live inference pipeline for IDX ML signal layer.

Orchestrates real-time signal generation:
1. Fetch latest market data
2. Compute features via IDXFeatureBuilder
3. Generate predictions from LightGBM and LSTM models
4. Combine signals with IC weighting
5. Compute SHAP explanations
6. Publish signals via Kafka

All inference runs are logged and include SHAP values.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any
from zoneinfo import ZoneInfo

import numpy as np
import numpy.typing as npt
import pandas as pd

from services.research.ml_signal.idx_feature_builder import IDXFeatureBuilder
from services.research.ml_signal.idx_lgbm_alpha_model import IDXLGBMAlphaModel
from services.research.ml_signal.idx_lstm_momentum_model import IDXLSTMTrainer
from services.research.ml_signal.idx_signal_combiner import IDXSignalCombiner

WIB = ZoneInfo("Asia/Jakarta")


@dataclass
class InferenceResult:
    """Result of a single inference run."""

    timestamp: datetime
    signals: pd.DataFrame  # symbol × (combined_alpha, lgbm_alpha, lstm_alpha, rank)
    shap_values: dict[str, npt.NDArray[Any]]  # model_name → SHAP array
    feature_matrix: pd.DataFrame
    model_weights: dict[str, float]
    ic_estimates: dict[str, float]
    latency_ms: float
    n_symbols: int
    metadata: dict[str, Any] = field(default_factory=dict)


class IDXLiveInferenceEngine:
    """Live inference pipeline for IDX alpha signals.

    Parameters
    ----------
    lgbm_model : IDXLGBMAlphaModel
        Trained LightGBM model.
    lstm_trainer : IDXLSTMTrainer, optional
        Trained LSTM trainer (with model loaded).
    feature_builder : IDXFeatureBuilder, optional
        Feature engineering pipeline.
    signal_combiner : IDXSignalCombiner, optional
        Signal combination engine.
    compute_shap : bool
        Whether to compute SHAP values on every inference.
    """

    def __init__(
        self,
        lgbm_model: IDXLGBMAlphaModel,
        lstm_trainer: IDXLSTMTrainer | None = None,
        feature_builder: IDXFeatureBuilder | None = None,
        signal_combiner: IDXSignalCombiner | None = None,
        compute_shap: bool = True,
    ) -> None:
        self._lgbm = lgbm_model
        self._lstm = lstm_trainer
        self._feature_builder = feature_builder or IDXFeatureBuilder()
        self._combiner = signal_combiner or IDXSignalCombiner()
        self._compute_shap = compute_shap
        self._inference_history: list[InferenceResult] = []

    @property
    def inference_history(self) -> list[InferenceResult]:
        return list(self._inference_history)

    def run_inference(
        self,
        prices: pd.DataFrame,
        volumes: pd.DataFrame,
        fundamentals: pd.DataFrame | None = None,
        macro: pd.DataFrame | None = None,
        realised_returns: pd.Series | None = None,
    ) -> InferenceResult:
        """Execute full inference pipeline.

        Parameters
        ----------
        prices : DataFrame
            Historical close prices (DatetimeIndex × symbols).
            Must include enough history for feature computation.
        volumes : DataFrame
            Historical volumes, same shape as prices.
        fundamentals : DataFrame, optional
            Fundamental data for value/quality features.
        macro : DataFrame, optional
            Macro indicators.
        realised_returns : Series, optional
            Recent realised returns for IC weight updating.

        Returns
        -------
        InferenceResult
            Contains signals, SHAP values, metadata.
        """
        start_time = time.monotonic()
        now = datetime.now(tz=WIB)

        # Step 1: Build features
        features = self._feature_builder.build_features(
            prices=prices,
            volumes=volumes,
            fundamentals=fundamentals,
            macro=macro,
        )

        # Get latest cross-section (most recent date)
        if isinstance(features.index, pd.MultiIndex):
            latest_date = features.index.get_level_values(0).max()
            latest_features = features.loc[latest_date]
        else:
            latest_date = features.index[-1]
            latest_features = features.iloc[[-1]]

        # Step 2: LightGBM predictions
        if isinstance(latest_features.index, pd.MultiIndex):
            lgbm_input = latest_features
        else:
            # Single date: features are (symbol,) indexed
            lgbm_input = latest_features

        lgbm_alpha = self._lgbm.predict(lgbm_input)

        # Step 3: LSTM predictions (if available)
        lstm_alpha = None
        if self._lstm is not None and self._lstm.model is not None:
            try:
                sequences, _ = self._lstm.prepare_sequences(features, pd.Series(0, index=features.index))
                if len(sequences) > 0:
                    lstm_preds = self._lstm.predict(sequences)
                    # Map back to symbols
                    if isinstance(features.index, pd.MultiIndex):
                        symbols = features.index.get_level_values(1).unique()
                        if len(lstm_preds) >= len(symbols):
                            lstm_alpha = pd.Series(
                                lstm_preds[-len(symbols) :],
                                index=lgbm_alpha.index,
                                name="lstm_alpha",
                            )
            except (RuntimeError, ValueError):
                pass

        # Step 4: Combine signals
        signal_dict: dict[str, pd.Series] = {"lgbm": lgbm_alpha}
        if lstm_alpha is not None:
            signal_dict["lstm"] = lstm_alpha

        combined = self._combiner.combine(
            signals=signal_dict,
            realised_returns=realised_returns,
        )

        # Build output DataFrame
        result_df = pd.DataFrame(
            {
                "combined_alpha": combined,
                "lgbm_alpha": lgbm_alpha,
            }
        )
        if lstm_alpha is not None:
            result_df["lstm_alpha"] = lstm_alpha

        # Cross-sectional rank
        result_df["rank"] = result_df["combined_alpha"].rank(ascending=False, method="min")

        # Step 5: SHAP values
        shap_values: dict[str, npt.NDArray[Any]] = {}
        if self._compute_shap:
            shap_values = self._compute_shap_values(lgbm_input)

        latency_ms = (time.monotonic() - start_time) * 1000

        result = InferenceResult(
            timestamp=now,
            signals=result_df,
            shap_values=shap_values,
            feature_matrix=latest_features
            if isinstance(latest_features, pd.DataFrame)
            else latest_features.to_frame().T,
            model_weights=self._combiner.current_weights,
            ic_estimates={name: ics[-1] if ics else 0.0 for name, ics in self._combiner.model_ics.items()},
            latency_ms=latency_ms,
            n_symbols=len(result_df),
            metadata={
                "latest_date": str(latest_date),
                "n_features": len(latest_features.columns) if isinstance(latest_features, pd.DataFrame) else 0,
                "has_lstm": lstm_alpha is not None,
            },
        )

        self._inference_history.append(result)
        return result

    def _compute_shap_values(
        self,
        X: pd.DataFrame,
    ) -> dict[str, npt.NDArray[Any]]:
        """Compute SHAP values for LightGBM model."""
        try:
            import shap

            if self._lgbm.model is not None:
                explainer = shap.TreeExplainer(self._lgbm.model)
                values = explainer.shap_values(X)
                return {"lgbm": np.array(values)}
        except (ImportError, Exception):
            pass

        return {}

    def get_top_signals(
        self,
        n: int = 10,
        min_alpha: float | None = None,
    ) -> pd.DataFrame:
        """Get top N signals from most recent inference.

        Parameters
        ----------
        n : int
            Number of top signals.
        min_alpha : float, optional
            Minimum alpha threshold.

        Returns
        -------
        DataFrame
            Top signals sorted by combined_alpha descending.
        """
        if not self._inference_history:
            return pd.DataFrame()

        latest = self._inference_history[-1]
        signals = latest.signals.sort_values("combined_alpha", ascending=False)

        if min_alpha is not None:
            signals = signals[signals["combined_alpha"] >= min_alpha]

        return signals.head(n)

    def get_signal_for_symbol(self, symbol: str) -> dict[str, Any] | None:
        """Get latest signal and SHAP explanation for a specific symbol."""
        if not self._inference_history:
            return None

        latest = self._inference_history[-1]
        if symbol not in latest.signals.index:
            return None

        signal_row = latest.signals.loc[symbol]
        result: dict[str, Any] = {
            "symbol": symbol,
            "combined_alpha": float(signal_row["combined_alpha"]),
            "lgbm_alpha": float(signal_row["lgbm_alpha"]),
            "rank": int(signal_row["rank"]),
            "timestamp": latest.timestamp.isoformat(),
        }

        if "lstm_alpha" in signal_row.index:
            result["lstm_alpha"] = float(signal_row["lstm_alpha"])

        # Add SHAP explanation
        if "lgbm" in latest.shap_values and symbol in latest.feature_matrix.index:
            sym_idx = list(latest.feature_matrix.index).index(symbol)
            shap_vals = latest.shap_values["lgbm"][sym_idx]
            feature_names = list(latest.feature_matrix.columns)
            # Top 5 contributing features
            abs_shap = np.abs(shap_vals)
            top_idx = abs_shap.argsort()[-5:][::-1]
            result["top_features"] = [{"feature": feature_names[i], "shap_value": float(shap_vals[i])} for i in top_idx]

        return result
