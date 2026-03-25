"""Model Training Manager for the Pyhron Research Platform.

Manages the training, evaluation, and registration of machine learning
models with MLflow experiment tracking. Supports scikit-learn and
PyTorch model workflows.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any, Optional
from uuid import UUID, uuid4

logger = logging.getLogger(__name__)


@dataclass
class ModelConfig:
    """Configuration for a model training run."""

    model_id: UUID = field(default_factory=uuid4)
    name: str = ""
    model_type: str = "sklearn"  # sklearn, pytorch, xgboost
    hyperparameters: dict[str, Any] = field(default_factory=dict)
    feature_columns: list[str] = field(default_factory=list)
    target_column: str = "target"
    train_split: float = 0.8
    random_seed: int = 42
    experiment_name: str = "default"

    def to_dict(self) -> dict[str, Any]:
        """Serialize model config."""
        return {
            "model_id": str(self.model_id),
            "name": self.name,
            "model_type": self.model_type,
            "hyperparameters": self.hyperparameters,
            "feature_columns": self.feature_columns,
            "target_column": self.target_column,
            "train_split": self.train_split,
            "random_seed": self.random_seed,
            "experiment_name": self.experiment_name,
        }


@dataclass
class ModelMetrics:
    """Evaluation metrics for a trained model."""

    accuracy: float | None = None
    precision: float | None = None
    recall: float | None = None
    f1_score: float | None = None
    mse: float | None = None
    rmse: float | None = None
    mae: float | None = None
    r2: float | None = None
    sharpe_ratio: float | None = None
    custom_metrics: dict[str, float] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Serialize metrics to a dictionary, excluding None values."""
        result: dict[str, Any] = {}
        for key in ("accuracy", "precision", "recall", "f1_score", "mse", "rmse", "mae", "r2", "sharpe_ratio"):
            val = getattr(self, key)
            if val is not None:
                result[key] = val
        result.update(self.custom_metrics)
        return result


@dataclass
class TrainedModel:
    """Record of a trained model."""

    model_id: UUID = field(default_factory=uuid4)
    name: str = ""
    config: ModelConfig | None = None
    metrics: ModelMetrics | None = None
    artifact_path: str | None = None
    mlflow_run_id: str | None = None
    status: str = "created"  # created, training, trained, registered, failed
    created_at: datetime = field(default_factory=lambda: datetime.now(tz=UTC))
    trained_at: datetime | None = None
    version: int = 1


class ModelTrainingManager:
    """Train, evaluate, and register ML models with MLflow tracking.

    Provides a high-level interface for the model training lifecycle:
    configuration, training with experiment tracking, evaluation on
    held-out data, and model registration for deployment.

    Parameters
    ----------
    mlflow_tracking_uri:
        MLflow tracking server URI.
    experiment_name:
        Default MLflow experiment name.
    """

    def __init__(
        self,
        mlflow_tracking_uri: str = "http://localhost:5000",
        experiment_name: str = "pyhron-models",
    ) -> None:
        self._tracking_uri = mlflow_tracking_uri
        self._experiment_name = experiment_name
        self._models: dict[str, TrainedModel] = {}
        logger.info("ModelTrainingManager initialized (mlflow=%s)", mlflow_tracking_uri)

    def train_model(
        self,
        name: str,
        train_data: Any,
        config: ModelConfig | None = None,
        **hyperparameters: Any,
    ) -> TrainedModel:
        """Train a machine learning model with MLflow tracking.

        Parameters
        ----------
        name:
            Model name for registration.
        train_data:
            Training data (pandas DataFrame expected).
        config:
            Model configuration. If ``None``, a default config is created
            using ``hyperparameters``.
        **hyperparameters:
            Additional hyperparameters merged into config.

        Returns
        -------
        TrainedModel
            Trained model record with metrics.
        """
        import mlflow
        import numpy as np
        import pandas as pd
        from sklearn.ensemble import GradientBoostingRegressor, RandomForestClassifier
        from sklearn.model_selection import train_test_split

        if config is None:
            config = ModelConfig(
                name=name,
                hyperparameters=hyperparameters,
                experiment_name=self._experiment_name,
            )
        else:
            config.hyperparameters.update(hyperparameters)

        record = TrainedModel(name=name, config=config, status="training")
        self._models[name] = record

        mlflow.set_tracking_uri(self._tracking_uri)
        mlflow.set_experiment(config.experiment_name)

        try:
            with mlflow.start_run(run_name=name) as run:
                record.mlflow_run_id = run.info.run_id

                # Log configuration
                mlflow.log_params(config.hyperparameters)
                mlflow.log_param("model_type", config.model_type)
                mlflow.log_param("train_split", config.train_split)

                # Prepare data
                df = train_data if isinstance(train_data, pd.DataFrame) else pd.DataFrame(train_data)
                feature_cols = config.feature_columns or [c for c in df.columns if c != config.target_column]
                X = df[feature_cols].values
                y = df[config.target_column].values

                X_train, X_test, y_train, y_test = train_test_split(
                    X, y, train_size=config.train_split, random_state=config.random_seed
                )

                # Train model based on type
                if config.model_type == "sklearn_classifier":
                    model = RandomForestClassifier(**config.hyperparameters, random_state=config.random_seed)
                    model.fit(X_train, y_train)
                    preds = model.predict(X_test)

                    from sklearn.metrics import accuracy_score, f1_score, precision_score, recall_score

                    metrics = ModelMetrics(
                        accuracy=float(accuracy_score(y_test, preds)),
                        precision=float(precision_score(y_test, preds, average="weighted", zero_division=0)),
                        recall=float(recall_score(y_test, preds, average="weighted", zero_division=0)),
                        f1_score=float(f1_score(y_test, preds, average="weighted", zero_division=0)),
                    )
                else:
                    # Default: regression
                    model = GradientBoostingRegressor(**config.hyperparameters, random_state=config.random_seed)
                    model.fit(X_train, y_train)
                    preds = model.predict(X_test)

                    from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score

                    mse = float(mean_squared_error(y_test, preds))
                    metrics = ModelMetrics(
                        mse=mse,
                        rmse=float(np.sqrt(mse)),
                        mae=float(mean_absolute_error(y_test, preds)),
                        r2=float(r2_score(y_test, preds)),
                    )

                # Log metrics
                for key, val in metrics.to_dict().items():
                    mlflow.log_metric(key, val)

                # Log model artifact
                mlflow.sklearn.log_model(model, artifact_path="model")

                record.metrics = metrics
                record.status = "trained"
                record.trained_at = datetime.now(tz=UTC)
                record.artifact_path = f"runs:/{run.info.run_id}/model"

        except Exception as exc:
            record.status = "failed"
            logger.error("Model training failed for '%s': %s", name, exc)
            raise

        logger.info("Trained model '%s': %s", name, record.metrics.to_dict() if record.metrics else "no metrics")
        return record

    def evaluate_model(
        self,
        name: str,
        test_data: Any,
    ) -> ModelMetrics:
        """Evaluate a trained model on new test data.

        Parameters
        ----------
        name:
            Name of the trained model to evaluate.
        test_data:
            Test data (pandas DataFrame expected).

        Returns
        -------
        ModelMetrics
            Evaluation metrics.

        Raises
        ------
        KeyError
            If the model is not found or not yet trained.
        """
        import mlflow
        import numpy as np
        import pandas as pd
        from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score

        if name not in self._models:
            raise KeyError(f"Model not found: {name}")
        record = self._models[name]
        if record.status != "trained" or not record.artifact_path:
            raise KeyError(f"Model '{name}' is not trained (status={record.status})")

        model = mlflow.sklearn.load_model(record.artifact_path)
        df = test_data if isinstance(test_data, pd.DataFrame) else pd.DataFrame(test_data)

        config = record.config
        assert config is not None
        feature_cols = config.feature_columns or [c for c in df.columns if c != config.target_column]
        X_test = df[feature_cols].values
        y_test = df[config.target_column].values

        preds = model.predict(X_test)
        mse = float(mean_squared_error(y_test, preds))

        metrics = ModelMetrics(
            mse=mse,
            rmse=float(np.sqrt(mse)),
            mae=float(mean_absolute_error(y_test, preds)),
            r2=float(r2_score(y_test, preds)),
        )

        logger.info("Evaluated model '%s': %s", name, metrics.to_dict())
        return metrics

    def register_model(
        self,
        name: str,
        model_name: str | None = None,
        description: str = "",
        tags: dict[str, str] | None = None,
    ) -> dict[str, Any]:
        """Register a trained model in the MLflow model registry.

        Parameters
        ----------
        name:
            Name of the trained model record.
        model_name:
            Registry name. Defaults to the model record name.
        description:
            Model description for the registry.
        tags:
            Tags to attach to the registered model version.

        Returns
        -------
        dict[str, Any]
            Registration result with model name and version.

        Raises
        ------
        KeyError
            If the model is not found or not trained.
        """
        import mlflow

        if name not in self._models:
            raise KeyError(f"Model not found: {name}")
        record = self._models[name]
        if record.status != "trained" or not record.artifact_path:
            raise KeyError(f"Model '{name}' is not trained")

        registry_name = model_name or name
        mlflow.set_tracking_uri(self._tracking_uri)

        result = mlflow.register_model(
            model_uri=record.artifact_path,
            name=registry_name,
            tags=tags,
        )

        record.status = "registered"
        record.version = int(result.version) if hasattr(result, "version") else 1

        logger.info("Registered model '%s' as '%s' (version %d)", name, registry_name, record.version)
        return {
            "model_name": registry_name,
            "version": record.version,
            "description": description,
            "run_id": record.mlflow_run_id,
        }

    def list_models(self, status: str | None = None) -> list[dict[str, Any]]:
        """List all tracked models.

        Parameters
        ----------
        status:
            Filter by status (``created``, ``training``, ``trained``,
            ``registered``, ``failed``).

        Returns
        -------
        list[dict[str, Any]]
            Model summaries.
        """
        results: list[dict[str, Any]] = []
        for name, record in self._models.items():
            if status and record.status != status:
                continue
            results.append({
                "model_id": str(record.model_id),
                "name": record.name,
                "status": record.status,
                "model_type": record.config.model_type if record.config else None,
                "metrics": record.metrics.to_dict() if record.metrics else None,
                "mlflow_run_id": record.mlflow_run_id,
                "trained_at": record.trained_at.isoformat() if record.trained_at else None,
                "version": record.version,
            })

        logger.info("Listed %d models (status=%s)", len(results), status)
        return results


__all__ = [
    "ModelConfig",
    "ModelMetrics",
    "ModelTrainingManager",
    "TrainedModel",
]
