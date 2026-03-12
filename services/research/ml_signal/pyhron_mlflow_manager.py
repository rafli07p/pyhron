"""MLflow experiment tracking for Pyhron ML signal layer.

Wraps MLflow for consistent experiment tracking, model registry,
and deployment gate enforcement across all ML training runs.
"""

from __future__ import annotations

import json
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator

import mlflow
import mlflow.lightgbm
import numpy.typing as npt
import mlflow.pytorch
import numpy as np
import pandas as pd

# Deployment gate thresholds
_DEFAULT_IC_GATE = 0.03
_DEFAULT_ICIR_GATE = 0.5


class PyhronMLflowManager:
    """MLflow wrapper for Pyhron ML experiments.

    Parameters
    ----------
    tracking_uri : str
        MLflow tracking server URI. Default uses local file store.
    experiment_name : str
        Name of the MLflow experiment.
    ic_gate : float
        Minimum IC for deployment.
    icir_gate : float
        Minimum ICIR for deployment.
    """

    def __init__(
        self,
        tracking_uri: str = "mlruns",
        experiment_name: str = "pyhron-idx-alpha",
        ic_gate: float = _DEFAULT_IC_GATE,
        icir_gate: float = _DEFAULT_ICIR_GATE,
    ) -> None:
        self._tracking_uri = tracking_uri
        self._experiment_name = experiment_name
        self._ic_gate = ic_gate
        self._icir_gate = icir_gate

        mlflow.set_tracking_uri(tracking_uri)
        mlflow.set_experiment(experiment_name)

    @contextmanager
    def start_run(
        self,
        run_name: str | None = None,
        tags: dict[str, str] | None = None,
    ) -> Iterator[mlflow.ActiveRun]:
        """Context manager for an MLflow run.

        Usage
        -----
        with manager.start_run("lgbm_v1") as run:
            manager.log_params(...)
            manager.log_metrics(...)
        """
        with mlflow.start_run(run_name=run_name) as run:
            if tags:
                mlflow.set_tags(tags)
            yield run

    def log_params(self, params: dict[str, Any]) -> None:
        """Log hyperparameters to current run."""
        # MLflow only accepts string values, flatten nested dicts
        flat = self._flatten_params(params)
        mlflow.log_params(flat)

    def log_metrics(
        self,
        metrics: dict[str, float],
        step: int | None = None,
    ) -> None:
        """Log metrics to current run."""
        for key, value in metrics.items():
            if isinstance(value, (int, float)) and not np.isnan(value):
                mlflow.log_metric(key, value, step=step)

    def log_cv_metrics(
        self,
        fold_metrics: list[dict[str, float]],
    ) -> None:
        """Log per-fold CV metrics."""
        for fold_idx, metrics in enumerate(fold_metrics):
            self.log_metrics(
                {f"cv_{k}": v for k, v in metrics.items()},
                step=fold_idx,
            )

        # Log aggregates
        all_keys: set[str] = set()
        for m in fold_metrics:
            all_keys.update(m.keys())

        for key in all_keys:
            values = [m[key] for m in fold_metrics if key in m]
            if values:
                self.log_metrics(
                    {
                        f"cv_mean_{key}": float(np.mean(values)),
                        f"cv_std_{key}": float(np.std(values)),
                    }
                )

    def log_ic_series(self, ic_series: pd.Series) -> None:
        """Log IC time series as metric steps."""
        for step, (date, ic_value) in enumerate(ic_series.items()):
            if not np.isnan(ic_value):
                mlflow.log_metric("ic", float(ic_value), step=step)

        # Log summary
        self.log_metrics(
            {
                "ic_mean": float(ic_series.mean()),
                "ic_std": float(ic_series.std()),
                "icir": float(ic_series.mean() / ic_series.std()) if ic_series.std() > 0 else 0.0,
            }
        )

    def log_feature_importance(
        self,
        importance: pd.Series,
        artifact_name: str = "feature_importance.json",
    ) -> None:
        """Log feature importance as artifact."""
        importance_dict = importance.to_dict()
        # Log top features as metrics
        for i, (feat, imp) in enumerate(importance.head(20).items()):
            mlflow.log_metric(f"feat_importance_{feat}", float(imp))

        # Save full importance as artifact
        tmp_path = Path("/tmp") / artifact_name
        tmp_path.write_text(json.dumps(importance_dict, indent=2, default=str))
        mlflow.log_artifact(str(tmp_path))
        tmp_path.unlink(missing_ok=True)

    def log_lgbm_model(
        self,
        model: Any,
        artifact_path: str = "lgbm_model",
        registered_name: str | None = None,
    ) -> None:
        """Log LightGBM model to MLflow."""
        mlflow.lightgbm.log_model(
            model,
            artifact_path=artifact_path,
            registered_model_name=registered_name,
        )

    def log_pytorch_model(
        self,
        model: Any,
        artifact_path: str = "lstm_model",
        registered_name: str | None = None,
    ) -> None:
        """Log PyTorch model to MLflow."""
        mlflow.pytorch.log_model(
            model,
            artifact_path=artifact_path,
            registered_model_name=registered_name,
        )

    def check_deployment_gate(
        self,
        metrics: dict[str, float],
    ) -> dict[str, Any]:
        """Check if model passes deployment gate.

        Returns
        -------
        dict with:
        - passes: bool
        - ic: float
        - icir: float
        - ic_gate: float
        - icir_gate: float
        - reason: str (if fails)
        """
        ic = metrics.get("mean_ic", metrics.get("ic_mean", 0.0))
        icir = metrics.get("icir", 0.0)

        passes = ic >= self._ic_gate and icir >= self._icir_gate

        result: dict[str, Any] = {
            "passes": passes,
            "ic": ic,
            "icir": icir,
            "ic_gate": self._ic_gate,
            "icir_gate": self._icir_gate,
        }

        if not passes:
            reasons = []
            if ic < self._ic_gate:
                reasons.append(f"IC {ic:.4f} < {self._ic_gate}")
            if icir < self._icir_gate:
                reasons.append(f"ICIR {icir:.4f} < {self._icir_gate}")
            result["reason"] = "; ".join(reasons)

        # Log gate result
        mlflow.log_metric("deployment_gate_passed", float(passes))
        mlflow.set_tag("deployment_ready", str(passes))

        return result

    def log_shap_summary(
        self,
        shap_values: npt.NDArray[Any],
        feature_names: list[str],
        artifact_name: str = "shap_summary.json",
    ) -> None:
        """Log SHAP value summary statistics."""
        mean_abs_shap = np.abs(shap_values).mean(axis=0)
        summary = dict(zip(feature_names, mean_abs_shap.tolist()))

        # Log top SHAP features as metrics
        sorted_features = sorted(summary.items(), key=lambda x: x[1], reverse=True)
        for feat, val in sorted_features[:20]:
            mlflow.log_metric(f"shap_mean_abs_{feat}", float(val))

        # Save full summary
        tmp_path = Path("/tmp") / artifact_name
        tmp_path.write_text(json.dumps(summary, indent=2))
        mlflow.log_artifact(str(tmp_path))
        tmp_path.unlink(missing_ok=True)

    @staticmethod
    def _flatten_params(
        params: dict[str, Any],
        prefix: str = "",
    ) -> dict[str, str]:
        """Flatten nested dict for MLflow param logging."""
        flat = {}
        for key, value in params.items():
            full_key = f"{prefix}{key}" if not prefix else f"{prefix}.{key}"
            if isinstance(value, dict):
                flat.update(PyhronMLflowManager._flatten_params(value, full_key))
            else:
                flat[full_key] = str(value)
        return flat
