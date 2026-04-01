"""Model registry: thin wrapper around MLflow with Pyhron conventions.

Provides point-in-time-safe model loading for backtesting and
standardised experiment naming.
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

import pandas as pd

from shared.platform_exception_hierarchy import PyhronError

logger = logging.getLogger(__name__)


class PyhronMLError(PyhronError):
    """ML pipeline error."""


class ModelRegistry:
    """Pyhron model registry wrapping MLflow.

    Parameters
    ----------
    mlflow_client:
        MLflow tracking client.  If ``None``, a default client is created
        on first use.
    """

    def __init__(self, mlflow_client: Any = None) -> None:
        self._client = mlflow_client

    def _get_client(self) -> Any:
        if self._client is None:
            import mlflow

            self._client = mlflow.tracking.MlflowClient()
        return self._client

    def register_model(
        self,
        name: str,
        model: Any,
        metrics: dict[str, float],
        feature_names: list[str],
        as_of: datetime,
    ) -> str:
        """Register a trained model in MLflow.

        Parameters
        ----------
        name:
            Model name (e.g. ``"xgb_ranker"``).
        model:
            Trained model object.
        metrics:
            Metric dict to log.
        feature_names:
            List of feature names used for training.
        as_of:
            Training data cutoff timestamp.

        Returns
        -------
        str
            MLflow run ID.
        """
        import mlflow

        experiment_name = f"pyhron/{name}"
        mlflow.set_experiment(experiment_name)

        with mlflow.start_run() as run:
            mlflow.log_metrics(metrics)
            mlflow.log_params(
                {
                    "feature_count": len(feature_names),
                    "as_of": as_of.isoformat(),
                }
            )
            mlflow.set_tags(
                {
                    "idx_universe": "true",
                    "pit_safe": "true",
                    "model_name": name,
                }
            )

            # Log feature names as artifact
            import json
            import tempfile

            with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
                json.dump(feature_names, f)
                f.flush()
                mlflow.log_artifact(f.name, "feature_names")

            # Log model
            try:
                mlflow.sklearn.log_model(model, "model")
            except Exception:
                # Fallback for non-sklearn models
                try:
                    mlflow.pytorch.log_model(model, "model")
                except Exception:
                    import pickle

                    with tempfile.NamedTemporaryFile(mode="wb", suffix=".pkl", delete=False) as pf:
                        pickle.dump(model, pf)
                        pf.flush()
                        mlflow.log_artifact(pf.name, "model")

            run_id = run.info.run_id
            logger.info(
                "model_registered",
                extra={"model_name": name, "run_id": run_id, "metrics": metrics},
            )
            return run_id

    def load_latest(self, name: str) -> tuple[Any, list[str]]:
        """Load the most recently registered model.

        Parameters
        ----------
        name:
            Model name.

        Returns
        -------
        tuple
            (model, feature_names)
        """
        import mlflow

        experiment_name = f"pyhron/{name}"
        experiment = mlflow.get_experiment_by_name(experiment_name)
        if experiment is None:
            raise PyhronMLError(f"No experiment found for model '{name}'")

        runs = mlflow.search_runs(
            experiment_ids=[experiment.experiment_id],
            order_by=["start_time DESC"],
            max_results=1,
        )
        if runs.empty:
            raise PyhronMLError(f"No runs found for model '{name}'")

        run_id = runs.iloc[0]["run_id"]
        model = mlflow.sklearn.load_model(f"runs:/{run_id}/model")

        # Load feature names
        client = self._get_client()
        artifacts = client.list_artifacts(run_id, "feature_names")
        feature_names: list[str] = []
        if artifacts:
            import json
            from pathlib import Path

            local_path = client.download_artifacts(run_id, "feature_names")
            for f in Path(local_path).glob("*.json"):
                feature_names = json.loads(f.read_text())
                break

        return model, feature_names

    def load_as_of(
        self,
        name: str,
        as_of: datetime,
    ) -> tuple[Any, list[str]]:
        """Load the model registered BEFORE ``as_of`` (PIT-safe).

        Parameters
        ----------
        name:
            Model name.
        as_of:
            Point-in-time boundary.

        Returns
        -------
        tuple
            (model, feature_names)

        Raises
        ------
        PyhronMLError
            If no model was registered before ``as_of``.
        """
        import mlflow

        experiment_name = f"pyhron/{name}"
        experiment = mlflow.get_experiment_by_name(experiment_name)
        if experiment is None:
            raise PyhronMLError(f"No experiment found for model '{name}'")

        # Search for runs that started before as_of
        as_of_ms = int(as_of.timestamp() * 1000)
        runs = mlflow.search_runs(
            experiment_ids=[experiment.experiment_id],
            filter_string=f"attributes.start_time < {as_of_ms}",
            order_by=["start_time DESC"],
            max_results=1,
        )
        if runs.empty:
            raise PyhronMLError(f"No model '{name}' registered before {as_of.isoformat()}")

        run_id = runs.iloc[0]["run_id"]
        model = mlflow.sklearn.load_model(f"runs:/{run_id}/model")

        client = self._get_client()
        feature_names: list[str] = []
        try:
            import json
            from pathlib import Path

            local_path = client.download_artifacts(run_id, "feature_names")
            for f in Path(local_path).glob("*.json"):
                feature_names = json.loads(f.read_text())
                break
        except Exception:
            logger.debug("feature_names_download_failed run_id=%s", run_id)

        return model, feature_names

    def compare_runs(self, name: str, n: int = 5) -> pd.DataFrame:
        """Return a leaderboard of the most recent runs.

        Parameters
        ----------
        name:
            Model name.
        n:
            Number of runs to return.

        Returns
        -------
        pd.DataFrame
            Leaderboard with run_id, start_time, and metrics.
        """
        import mlflow

        experiment_name = f"pyhron/{name}"
        experiment = mlflow.get_experiment_by_name(experiment_name)
        if experiment is None:
            return pd.DataFrame()

        return mlflow.search_runs(
            experiment_ids=[experiment.experiment_id],
            order_by=["start_time DESC"],
            max_results=n,
        )
