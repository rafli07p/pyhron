"""LightGBM cross-sectional alpha model for IDX.

Trains a LightGBM regressor on rank-normalised features to predict
cross-sectional forward returns. Uses purged K-fold CV for hyperparameter
selection and deploys via deployment gates (IC >= 0.03, ICIR >= 0.5).
"""

from __future__ import annotations

import pickle
from pathlib import Path
from typing import Any

import lightgbm as lgb
import numpy as np
import pandas as pd
from scipy.stats import spearmanr

from services.research.ml_signal.purged_kfold import PurgedKFold

# Default LightGBM hyperparameters for cross-sectional alpha
_DEFAULT_PARAMS: dict[str, Any] = {
    "objective": "regression",
    "metric": "rmse",
    "boosting_type": "gbdt",
    "num_leaves": 31,
    "learning_rate": 0.05,
    "feature_fraction": 0.8,
    "bagging_fraction": 0.8,
    "bagging_freq": 5,
    "min_child_samples": 50,
    "lambda_l1": 0.1,
    "lambda_l2": 0.1,
    "max_depth": 6,
    "n_estimators": 500,
    "verbose": -1,
    "seed": 42,
    "n_jobs": -1,
}

# Deployment gates
_MIN_IC = 0.03
_MIN_ICIR = 0.5


class IDXLGBMAlphaModel:
    """LightGBM cross-sectional alpha model.

    Parameters
    ----------
    params : dict, optional
        LightGBM hyperparameters. Merged with defaults.
    n_splits : int
        Number of purged CV folds.
    purge_days : int
        Purge window for cross-validation (must be >= label horizon).
    min_ic : float
        Minimum Information Coefficient for deployment gate.
    min_icir : float
        Minimum IC Information Ratio for deployment gate.
    """

    def __init__(
        self,
        params: dict[str, Any] | None = None,
        n_splits: int = 5,
        purge_days: int = 10,
        min_ic: float = _MIN_IC,
        min_icir: float = _MIN_ICIR,
    ) -> None:
        self._params = {**_DEFAULT_PARAMS, **(params or {})}
        self._n_splits = n_splits
        self._purge_days = purge_days
        self._min_ic = min_ic
        self._min_icir = min_icir
        self._model: lgb.LGBMRegressor | None = None
        self._feature_names: list[str] = []
        self._cv_metrics: dict[str, float] = {}
        self._fold_ics: list[float] = []

    @property
    def model(self) -> lgb.LGBMRegressor | None:
        return self._model

    @property
    def cv_metrics(self) -> dict[str, float]:
        return dict(self._cv_metrics)

    @property
    def feature_names(self) -> list[str]:
        return list(self._feature_names)

    @property
    def passes_deployment_gate(self) -> bool:
        """Check if model meets deployment criteria."""
        ic = self._cv_metrics.get("mean_ic", 0.0)
        icir = self._cv_metrics.get("icir", 0.0)
        return ic >= self._min_ic and icir >= self._min_icir

    def train(
        self,
        X: pd.DataFrame,
        y: pd.Series,
        sample_weight: pd.Series | None = None,
    ) -> dict[str, float]:
        """Train model with purged cross-validation.

        Parameters
        ----------
        X : DataFrame
            Feature matrix with MultiIndex (date, symbol).
        y : Series
            Rank-normalised forward return labels.
        sample_weight : Series, optional
            Sample weights (e.g., inverse volatility).

        Returns
        -------
        dict
            Cross-validation metrics: mean_ic, std_ic, icir, mean_rmse,
            fold_ics, passes_gate.
        """
        self._feature_names = list(X.columns)
        cv = PurgedKFold(
            n_splits=self._n_splits,
            purge_days=self._purge_days,
        )

        fold_ics: list[float] = []
        fold_rmses: list[float] = []

        for train_idx, test_idx in cv.split(X, y):
            X_train, X_test = X.iloc[train_idx], X.iloc[test_idx]
            y_train, y_test = y.iloc[train_idx], y.iloc[test_idx]

            sw_train = None
            if sample_weight is not None:
                sw_train = sample_weight.iloc[train_idx]

            model = lgb.LGBMRegressor(**self._params)
            model.fit(
                X_train, y_train,
                sample_weight=sw_train,
                eval_set=[(X_test, y_test)],
                callbacks=[lgb.early_stopping(50, verbose=False), lgb.log_evaluation(period=0)],
            )

            y_pred = model.predict(X_test)

            # Compute IC (Spearman rank correlation)
            if len(y_test) > 2:
                ic, _ = spearmanr(y_test, y_pred)
                if not np.isnan(ic):
                    fold_ics.append(float(ic))

            # RMSE
            rmse = float(np.sqrt(np.mean((y_test.values - y_pred) ** 2)))
            fold_rmses.append(rmse)

        self._fold_ics = fold_ics
        mean_ic = float(np.mean(fold_ics)) if fold_ics else 0.0
        std_ic = float(np.std(fold_ics)) if fold_ics else 1.0
        icir = mean_ic / std_ic if std_ic > 0 else 0.0

        self._cv_metrics = {
            "mean_ic": mean_ic,
            "std_ic": std_ic,
            "icir": icir,
            "mean_rmse": float(np.mean(fold_rmses)) if fold_rmses else 0.0,
            "n_folds": len(fold_ics),
            "passes_gate": float(self.passes_deployment_gate),
        }

        # Train final model on all data
        self._model = lgb.LGBMRegressor(**self._params)
        sw = sample_weight if sample_weight is not None else None
        self._model.fit(X, y, sample_weight=sw)

        return self._cv_metrics

    def predict(self, X: pd.DataFrame) -> pd.Series:
        """Generate alpha predictions.

        Parameters
        ----------
        X : DataFrame
            Feature matrix (same columns as training).

        Returns
        -------
        Series
            Predicted alpha scores, same index as X.
        """
        if self._model is None:
            raise RuntimeError("Model not trained. Call train() first.")

        predictions = self._model.predict(X)
        return pd.Series(predictions, index=X.index, name="lgbm_alpha")

    def predict_with_rank(self, X: pd.DataFrame) -> pd.DataFrame:
        """Generate predictions with cross-sectional rank.

        Returns DataFrame with columns: lgbm_alpha, lgbm_rank.
        Rank is computed per date cross-section.
        """
        alpha = self.predict(X)
        result = alpha.to_frame()

        if isinstance(X.index, pd.MultiIndex):
            result["lgbm_rank"] = result.groupby(level=0)["lgbm_alpha"].rank(
                ascending=False, method="min"
            )
        else:
            result["lgbm_rank"] = result["lgbm_alpha"].rank(ascending=False, method="min")

        return result

    def get_feature_importance(self, importance_type: str = "gain") -> pd.Series:
        """Get feature importance from trained model.

        Parameters
        ----------
        importance_type : str
            'gain', 'split', or 'weight'.

        Returns
        -------
        Series
            Feature importance sorted descending.
        """
        if self._model is None:
            raise RuntimeError("Model not trained.")

        importance = self._model.feature_importances_
        result = pd.Series(importance, index=self._feature_names, name="importance")
        return result.sort_values(ascending=False)

    def save(self, path: str | Path) -> None:
        """Save model to disk."""
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "wb") as f:
            pickle.dump({
                "model": self._model,
                "feature_names": self._feature_names,
                "cv_metrics": self._cv_metrics,
                "params": self._params,
                "fold_ics": self._fold_ics,
            }, f)

    def load(self, path: str | Path) -> None:
        """Load model from disk."""
        with open(path, "rb") as f:
            data = pickle.load(f)  # noqa: S301
        self._model = data["model"]
        self._feature_names = data["feature_names"]
        self._cv_metrics = data["cv_metrics"]
        self._params = data["params"]
        self._fold_ics = data.get("fold_ics", [])

    def compute_ic_series(
        self,
        X: pd.DataFrame,
        y: pd.Series,
    ) -> pd.Series:
        """Compute rolling IC series per date cross-section.

        Useful for monitoring model performance over time.
        """
        if self._model is None:
            raise RuntimeError("Model not trained.")

        predictions = self.predict(X)

        if not isinstance(X.index, pd.MultiIndex):
            ic, _ = spearmanr(y, predictions)
            return pd.Series([ic], index=["overall"], name="ic")

        # Group by date and compute IC per cross-section
        combined = pd.DataFrame({"y": y, "pred": predictions})
        dates = combined.index.get_level_values(0).unique()

        ics = {}
        for dt in dates:
            group = combined.loc[dt]
            if len(group) < 3:
                continue
            ic, _ = spearmanr(group["y"], group["pred"])
            if not np.isnan(ic):
                ics[dt] = ic

        return pd.Series(ics, name="ic")
