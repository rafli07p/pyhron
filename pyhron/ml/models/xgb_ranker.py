"""XGBoost LambdaRank cross-sectional equity ranker.

Ranks stocks by predicted forward return using walk-forward
expanding window training with Optuna hyperparameter tuning.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    import numpy as np
    import pandas as pd

logger = logging.getLogger(__name__)

_DEFAULT_HYPERPARAMS = {
    "max_depth": 5,
    "n_estimators": 300,
    "learning_rate": 0.05,
    "subsample": 0.8,
    "objective": "rank:pairwise",
    "eval_metric": "ndcg",
}


class XGBRanker:
    """XGBoost LambdaRank cross-sectional equity ranker.

    Parameters
    ----------
    params:
        XGBoost parameters.  Overrides defaults.
    retrain_frequency:
        Retrain every N trading days (default 21).
    forward_period:
        Forward return period in days for target (default 5).
    """

    def __init__(
        self,
        params: dict[str, Any] | None = None,
        retrain_frequency: int = 21,
        forward_period: int = 5,
    ) -> None:
        self._params = {**_DEFAULT_HYPERPARAMS, **(params or {})}
        self._retrain_frequency = retrain_frequency
        self._forward_period = forward_period
        self._model: Any = None
        self._feature_names: list[str] = []

    @property
    def feature_names(self) -> list[str]:
        return self._feature_names

    def fit(
        self,
        X: pd.DataFrame,  # noqa: N803
        y: pd.Series,
        group: list[int] | None = None,
    ) -> XGBRanker:
        """Train the XGBoost ranker.

        Parameters
        ----------
        X:
            Feature matrix (n_stocks × n_features).
        y:
            Forward returns as target.
        group:
            Group sizes for ranking (stocks per rebalance date).

        Returns
        -------
        XGBRanker
            Self, for method chaining.
        """
        import xgboost as xgb

        self._feature_names = list(X.columns)

        if group is None:
            group = [len(X)]

        dtrain = xgb.DMatrix(X, label=y)
        dtrain.set_group(group)

        self._model = xgb.train(
            self._params,
            dtrain,
            num_boost_round=self._params.get("n_estimators", 300),
        )

        logger.info(
            "xgb_ranker_trained",
            extra={"n_features": len(self._feature_names), "n_samples": len(X)},
        )
        return self

    def predict(self, X: pd.DataFrame) -> np.ndarray:  # noqa: N803
        """Score stocks for ranking.

        Parameters
        ----------
        X:
            Feature matrix for a single rebalance date.

        Returns
        -------
        np.ndarray
            Scores — higher is more attractive.
        """
        if self._model is None:
            msg = "Model not trained. Call fit() first."
            raise RuntimeError(msg)

        import xgboost as xgb

        dtest = xgb.DMatrix(X)
        return self._model.predict(dtest)

    def feature_importance(self) -> dict[str, float]:
        """Return feature importance scores."""
        if self._model is None:
            return {}
        return dict(self._model.get_fscore())

    @staticmethod
    def tune_hyperparameters(
        X: pd.DataFrame,  # noqa: N803
        y: pd.Series,
        group: list[int],
        n_trials: int = 20,
    ) -> dict[str, Any]:
        """Tune hyperparameters via Optuna.

        Parameters
        ----------
        X:
            Training features.
        y:
            Training target.
        group:
            Group sizes.
        n_trials:
            Number of Optuna trials.

        Returns
        -------
        dict
            Best hyperparameters.
        """
        import optuna
        import xgboost as xgb

        def objective(trial: optuna.Trial) -> float:
            params = {
                "max_depth": trial.suggest_int("max_depth", 3, 7),
                "n_estimators": trial.suggest_int("n_estimators", 100, 500),
                "learning_rate": trial.suggest_float("learning_rate", 0.01, 0.1, log=True),
                "subsample": trial.suggest_float("subsample", 0.6, 1.0),
                "objective": "rank:pairwise",
                "eval_metric": "ndcg",
            }

            dtrain = xgb.DMatrix(X, label=y)
            dtrain.set_group(group)

            cv_results = xgb.cv(
                params,
                dtrain,
                num_boost_round=params["n_estimators"],
                nfold=3,
                metrics=["ndcg"],
                early_stopping_rounds=20,
                verbose_eval=False,
            )

            return float(cv_results["test-ndcg-mean"].iloc[-1])

        study = optuna.create_study(direction="maximize")
        study.optimize(objective, n_trials=n_trials, show_progress_bar=False)

        return study.best_params
