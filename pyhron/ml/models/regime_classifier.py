"""Hidden Markov Model regime detector (bull/bear/sideways).

Uses Gaussian mixture emissions to classify the current market regime
based on index returns, volatility, and macro features.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any, Literal

import numpy as np

if TYPE_CHECKING:
    import pandas as pd

logger = logging.getLogger(__name__)

_REGIME_LABELS = {0: "bull", 1: "bear", 2: "sideways"}


class RegimeClassifier:
    """HMM-based regime detector.

    Parameters
    ----------
    n_states:
        Number of hidden states (default 3: bull/bear/sideways).
    n_iter:
        Number of EM iterations.
    feature_columns:
        Feature column names for the observation matrix.
    """

    def __init__(
        self,
        n_states: int = 3,
        n_iter: int = 100,
        feature_columns: list[str] | None = None,
    ) -> None:
        self._n_states = n_states
        self._n_iter = n_iter
        self._feature_columns = feature_columns or [
            "ihsg_log_ret_5d",
            "ihsg_vol_20d",
            "idr_usd_change_5d",
            "vix_level",
        ]
        self._model: Any = None
        self._regime_map: dict[int, str] = {}

    def fit(self, features_df: pd.DataFrame) -> RegimeClassifier:
        """Fit the HMM on historical regime features.

        Parameters
        ----------
        features_df:
            DataFrame with feature columns.

        Returns
        -------
        RegimeClassifier
            Self.
        """
        from hmmlearn.hmm import GaussianHMM

        X = features_df[self._feature_columns].dropna().values

        self._model = GaussianHMM(
            n_components=self._n_states,
            covariance_type="full",
            n_iter=self._n_iter,
            random_state=42,
        )
        self._model.fit(X)

        # Map states to regimes based on mean return of first feature
        means = self._model.means_[:, 0]
        sorted_indices = np.argsort(means)

        # Lowest mean return = bear, middle = sideways, highest = bull
        self._regime_map = {
            int(sorted_indices[0]): "bear",
            int(sorted_indices[1]): "sideways",
            int(sorted_indices[2]): "bull",
        }

        logger.info(
            "regime_classifier_fitted",
            extra={
                "n_states": self._n_states,
                "regime_map": self._regime_map,
                "means": means.tolist(),
            },
        )
        return self

    def predict(self, features_df: pd.DataFrame) -> list[str]:
        """Predict regime for each observation.

        Parameters
        ----------
        features_df:
            DataFrame with feature columns.

        Returns
        -------
        list[str]
            List of regime labels.
        """
        if self._model is None:
            msg = "Model not fitted. Call fit() first."
            raise RuntimeError(msg)

        X = features_df[self._feature_columns].dropna().values
        states = self._model.predict(X)
        return [self._regime_map.get(int(s), "sideways") for s in states]

    def current_regime(self, features_df: pd.DataFrame) -> Literal["bull", "bear", "sideways"]:
        """Predict the current regime from the latest observation.

        Parameters
        ----------
        features_df:
            DataFrame with at least one row of feature values.

        Returns
        -------
        str
            Current regime: ``"bull"``, ``"bear"``, or ``"sideways"``.
        """
        if self._model is None:
            msg = "Model not fitted. Call fit() first."
            raise RuntimeError(msg)

        X = features_df[self._feature_columns].dropna().values
        if len(X) == 0:
            return "sideways"

        states = self._model.predict(X)
        current_state = int(states[-1])
        return self._regime_map.get(current_state, "sideways")

    def regime_confidence(self, features_df: pd.DataFrame) -> tuple[str, float]:
        """Return current regime and confidence.

        Parameters
        ----------
        features_df:
            DataFrame with feature columns.

        Returns
        -------
        tuple
            (regime, confidence) where confidence is the posterior
            probability of the predicted state.
        """
        if self._model is None:
            msg = "Model not fitted"
            raise RuntimeError(msg)

        X = features_df[self._feature_columns].dropna().values
        if len(X) == 0:
            return "sideways", 0.0

        posteriors = self._model.predict_proba(X)
        last_posterior = posteriors[-1]
        state = int(np.argmax(last_posterior))
        regime = self._regime_map.get(state, "sideways")
        confidence = float(last_posterior[state])
        return regime, confidence
