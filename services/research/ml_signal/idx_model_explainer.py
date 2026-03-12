"""SHAP-based model explainability for IDX ML signal layer.

Provides feature attribution for every live inference run,
model-level feature importance analysis, and cross-sectional
explanation reports.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import numpy as np
import pandas as pd
import shap

from services.research.ml_signal.idx_lgbm_alpha_model import IDXLGBMAlphaModel


@dataclass
class ExplanationResult:
    """SHAP explanation for a set of predictions."""

    shap_values: np.ndarray  # (n_samples, n_features)
    feature_names: list[str]
    base_value: float
    feature_importance: pd.Series  # mean |SHAP| per feature
    top_features_per_sample: list[list[dict[str, Any]]]  # per-sample top features


class IDXModelExplainer:
    """SHAP explainer for Pyhron ML models.

    Parameters
    ----------
    model : IDXLGBMAlphaModel
        Trained LightGBM model to explain.
    background_samples : int
        Number of background samples for SHAP (for KernelExplainer fallback).
    """

    def __init__(
        self,
        model: IDXLGBMAlphaModel,
        background_samples: int = 100,
    ) -> None:
        self._model = model
        self._background_samples = background_samples
        self._explainer: shap.TreeExplainer | None = None

    def _get_explainer(self) -> shap.TreeExplainer:
        """Lazily initialise SHAP TreeExplainer."""
        if self._explainer is None:
            if self._model.model is None:
                raise RuntimeError("Model not trained.")
            self._explainer = shap.TreeExplainer(self._model.model)
        return self._explainer

    def explain(
        self,
        X: pd.DataFrame,
        top_n: int = 5,
    ) -> ExplanationResult:
        """Compute SHAP values for a feature matrix.

        Parameters
        ----------
        X : DataFrame
            Feature matrix (n_samples × n_features).
        top_n : int
            Number of top contributing features per sample.

        Returns
        -------
        ExplanationResult
        """
        explainer = self._get_explainer()
        shap_values = explainer.shap_values(X)
        shap_array = np.array(shap_values)

        feature_names = list(X.columns)

        # Global feature importance (mean absolute SHAP)
        mean_abs_shap = np.abs(shap_array).mean(axis=0)
        importance = pd.Series(
            mean_abs_shap,
            index=feature_names,
            name="mean_abs_shap",
        ).sort_values(ascending=False)

        # Per-sample top features
        top_features_per_sample = []
        for i in range(len(X)):
            sample_shap = shap_array[i]
            abs_shap = np.abs(sample_shap)
            top_idx = abs_shap.argsort()[-top_n:][::-1]
            sample_top = [
                {
                    "feature": feature_names[j],
                    "shap_value": float(sample_shap[j]),
                    "feature_value": float(X.iloc[i, j]),
                    "direction": "positive" if sample_shap[j] > 0 else "negative",
                }
                for j in top_idx
            ]
            top_features_per_sample.append(sample_top)

        base_value = float(explainer.expected_value)
        if isinstance(base_value, np.ndarray):
            base_value = float(base_value[0])

        return ExplanationResult(
            shap_values=shap_array,
            feature_names=feature_names,
            base_value=base_value,
            feature_importance=importance,
            top_features_per_sample=top_features_per_sample,
        )

    def explain_symbol(
        self,
        X: pd.DataFrame,
        symbol: str,
        top_n: int = 10,
    ) -> dict[str, Any]:
        """Explain prediction for a specific symbol.

        Parameters
        ----------
        X : DataFrame
            Feature matrix with symbol in index.
        symbol : str
            Target symbol.
        top_n : int
            Number of top features to return.

        Returns
        -------
        dict with symbol explanation.
        """
        if symbol not in X.index:
            raise ValueError(f"Symbol {symbol} not in feature matrix.")

        # Get single row
        sample = X.loc[[symbol]]
        explanation = self.explain(sample, top_n=top_n)

        prediction = float(self._model.predict(sample).iloc[0])

        return {
            "symbol": symbol,
            "prediction": prediction,
            "base_value": explanation.base_value,
            "top_features": explanation.top_features_per_sample[0],
            "all_shap_values": dict(zip(
                explanation.feature_names,
                explanation.shap_values[0].tolist(),
            )),
        }

    def feature_interaction(
        self,
        X: pd.DataFrame,
        feature_a: str,
        feature_b: str,
    ) -> pd.DataFrame:
        """Compute SHAP interaction values between two features.

        Returns DataFrame with columns: feature_a_value, feature_b_value,
        interaction_shap.
        """
        explainer = self._get_explainer()

        try:
            interaction_values = explainer.shap_interaction_values(X)
            interaction_array = np.array(interaction_values)
        except Exception:
            # Fallback: approximate interaction
            return pd.DataFrame(columns=["feature_a_value", "feature_b_value", "interaction_shap"])

        feat_names = list(X.columns)
        idx_a = feat_names.index(feature_a)
        idx_b = feat_names.index(feature_b)

        return pd.DataFrame({
            "feature_a_value": X[feature_a].values,
            "feature_b_value": X[feature_b].values,
            "interaction_shap": interaction_array[:, idx_a, idx_b],
        }, index=X.index)

    def cross_sectional_report(
        self,
        X: pd.DataFrame,
        date_label: str = "",
    ) -> dict[str, Any]:
        """Generate cross-sectional explanation report.

        Returns dict with:
        - date: str
        - n_symbols: int
        - feature_importance: dict (feature → mean |SHAP|)
        - factor_group_importance: dict (group → mean |SHAP|)
        - top_long_explanations: list (top 5 long signals with explanations)
        - top_short_explanations: list (top 5 short signals with explanations)
        """
        explanation = self.explain(X, top_n=5)
        predictions = self._model.predict(X)

        # Factor group aggregation
        group_importance = self._aggregate_factor_groups(explanation)

        # Top long/short
        sorted_idx = predictions.argsort().to_numpy()
        top_long_idx = sorted_idx[-5:][::-1] if len(sorted_idx) >= 5 else sorted_idx[::-1]
        top_short_idx = sorted_idx[:5] if len(sorted_idx) >= 5 else sorted_idx

        def _build_explanation(idx_list: np.ndarray | pd.Index) -> list[dict[str, Any]]:
            results = []
            for i in idx_list:
                symbol = X.index[i] if not isinstance(X.index[i], tuple) else X.index[i]
                results.append({
                    "symbol": str(symbol),
                    "prediction": float(predictions.iloc[i]),
                    "top_features": explanation.top_features_per_sample[i],
                })
            return results

        return {
            "date": date_label,
            "n_symbols": len(X),
            "feature_importance": explanation.feature_importance.to_dict(),
            "factor_group_importance": group_importance,
            "top_long_explanations": _build_explanation(top_long_idx),
            "top_short_explanations": _build_explanation(top_short_idx),
        }

    @staticmethod
    def _aggregate_factor_groups(explanation: ExplanationResult) -> dict[str, float]:
        """Aggregate SHAP importance by factor group prefix."""
        groups: dict[str, list[float]] = {}
        prefix_map = {
            "mom_": "momentum",
            "val_": "value",
            "qual_": "quality",
            "vol_": "volatility",
            "liq_": "liquidity",
            "macro_": "macro",
            "tech_": "technical",
        }

        for feat, imp in explanation.feature_importance.items():
            group = "other"
            feat_str = str(feat)
            for prefix, group_name in prefix_map.items():
                if feat_str.startswith(prefix):
                    group = group_name
                    break
            groups.setdefault(group, []).append(imp)

        return {
            group: float(np.mean(values))
            for group, values in sorted(groups.items(), key=lambda x: -np.mean(x[1]))
        }
