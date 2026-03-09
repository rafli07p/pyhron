"""ML Pipelines for the Enthropy Research Platform.

Production-grade machine learning pipeline with PyTorch model training,
scikit-learn preprocessing, and MLflow experiment tracking. Designed
for financial time-series prediction tasks including return forecasting,
volatility estimation, and regime classification.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from typing import Any, Optional

import mlflow
import mlflow.pytorch
import numpy as np
import torch
import torch.nn as nn
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from torch.utils.data import DataLoader, TensorDataset

logger = logging.getLogger(__name__)


@dataclass
class PipelineConfig:
    """Configuration for an ML training pipeline run."""

    experiment_name: str = "enthropy-ml-pipeline"
    run_name: str = "default_run"
    input_dim: int = 10
    hidden_dims: list[int] = field(default_factory=lambda: [128, 64, 32])
    output_dim: int = 1
    dropout_rate: float = 0.2
    learning_rate: float = 1e-3
    weight_decay: float = 1e-5
    batch_size: int = 64
    epochs: int = 50
    early_stopping_patience: int = 10
    train_split: float = 0.7
    val_split: float = 0.15
    test_split: float = 0.15
    random_seed: int = 42
    device: str = "cpu"
    mlflow_tracking_uri: str = "http://localhost:5000"
    task_type: str = "regression"  # regression, classification


class FinancialNet(nn.Module):
    """Multi-layer feedforward network for financial prediction.

    A flexible deep neural network with batch normalization, dropout,
    and residual connections for tabular financial data. Supports both
    regression and classification output heads.

    Parameters
    ----------
    input_dim:
        Number of input features.
    hidden_dims:
        List of hidden layer sizes.
    output_dim:
        Number of output units.
    dropout_rate:
        Dropout probability applied after each hidden layer.
    task_type:
        ``regression`` for continuous targets or ``classification``
        for discrete labels.
    """

    def __init__(
        self,
        input_dim: int,
        hidden_dims: list[int],
        output_dim: int,
        dropout_rate: float = 0.2,
        task_type: str = "regression",
    ) -> None:
        super().__init__()
        self.task_type = task_type

        layers: list[nn.Module] = []
        prev_dim = input_dim

        for i, hidden_dim in enumerate(hidden_dims):
            layers.append(nn.Linear(prev_dim, hidden_dim))
            layers.append(nn.BatchNorm1d(hidden_dim))
            layers.append(nn.ReLU(inplace=True))
            layers.append(nn.Dropout(p=dropout_rate))
            prev_dim = hidden_dim

        self.feature_extractor = nn.Sequential(*layers)
        self.output_head = nn.Linear(prev_dim, output_dim)

        # Residual projection if input/output dims differ
        self.residual_proj: nn.Linear | None = None
        if input_dim != prev_dim:
            self.residual_proj = nn.Linear(input_dim, prev_dim)

        # Initialize weights with Xavier uniform
        self._init_weights()

    def _init_weights(self) -> None:
        """Apply Xavier uniform initialization to linear layers."""
        for module in self.modules():
            if isinstance(module, nn.Linear):
                nn.init.xavier_uniform_(module.weight)
                if module.bias is not None:
                    nn.init.zeros_(module.bias)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """Forward pass through the network.

        Parameters
        ----------
        x:
            Input tensor of shape ``(batch_size, input_dim)``.

        Returns
        -------
        torch.Tensor
            Output predictions.
        """
        features = self.feature_extractor(x)

        # Add residual connection
        if self.residual_proj is not None:
            residual = self.residual_proj(x)
            features = features + residual

        output = self.output_head(features)

        if self.task_type == "classification":
            output = torch.softmax(output, dim=-1)

        return output


class MLPipeline:
    """End-to-end ML training pipeline with PyTorch and MLflow.

    Implements a complete machine learning workflow for financial
    prediction tasks:

    1. **prepare_data**: Splits and scales features using scikit-learn's
       ``StandardScaler``, creates PyTorch ``DataLoader`` instances for
       train/val/test sets.
    2. **build_model**: Constructs a ``FinancialNet`` (``nn.Module``)
       with configurable hidden layers, batch norm, dropout, and
       residual connections.
    3. **train**: Runs the training loop with AdamW optimizer, gradient
       clipping, and early stopping based on validation loss.
    4. **evaluate**: Computes regression metrics (MSE, RMSE, MAE, R2)
       or classification metrics (accuracy), plus financial metrics
       like directional accuracy and information coefficient.
    5. **log_to_mlflow**: Logs all parameters, per-epoch metrics,
       evaluation results, and the trained model artifact to MLflow.

    Parameters
    ----------
    config:
        Pipeline configuration. If ``None``, uses default settings.

    Example
    -------
    >>> import pandas as pd
    >>> pipeline = MLPipeline(PipelineConfig(
    ...     input_dim=20,
    ...     hidden_dims=[128, 64],
    ...     epochs=30,
    ... ))
    >>> pipeline.prepare_data(features_df, targets_series)
    >>> model = pipeline.build_model()
    >>> metrics = pipeline.train()
    >>> eval_metrics = pipeline.evaluate()
    >>> pipeline.log_to_mlflow()
    """

    def __init__(self, config: PipelineConfig | None = None) -> None:
        self.config = config or PipelineConfig()
        self._scaler = StandardScaler()
        self._model: FinancialNet | None = None
        self._optimizer: torch.optim.Optimizer | None = None
        self._criterion: nn.Module | None = None
        self._device = torch.device(self.config.device)

        # Data splits
        self._X_train: np.ndarray | None = None
        self._X_val: np.ndarray | None = None
        self._X_test: np.ndarray | None = None
        self._y_train: np.ndarray | None = None
        self._y_val: np.ndarray | None = None
        self._y_test: np.ndarray | None = None

        # Data loaders
        self._train_loader: DataLoader[Any] | None = None
        self._val_loader: DataLoader[Any] | None = None
        self._test_loader: DataLoader[Any] | None = None

        # Training history
        self._train_losses: list[float] = []
        self._val_losses: list[float] = []
        self._best_val_loss: float = float("inf")
        self._best_model_state: dict[str, Any] | None = None
        self._training_time: float = 0.0
        self._eval_metrics: dict[str, float] = {}

        logger.info(
            "MLPipeline initialized (input=%d, hidden=%s, output=%d, task=%s)",
            self.config.input_dim, self.config.hidden_dims,
            self.config.output_dim, self.config.task_type,
        )

    def prepare_data(
        self,
        features: np.ndarray | Any,
        targets: np.ndarray | Any,
        feature_names: list[str] | None = None,
    ) -> dict[str, int]:
        """Prepare and split data for training.

        Applies ``StandardScaler`` to features and creates three-way
        train/validation/test splits.

        Parameters
        ----------
        features:
            Feature matrix of shape ``(n_samples, n_features)``.
            Accepts numpy arrays or pandas DataFrames.
        targets:
            Target vector of shape ``(n_samples,)`` or
            ``(n_samples, output_dim)``.
        feature_names:
            Optional feature names for logging.

        Returns
        -------
        dict[str, int]
            Split sizes: ``train``, ``val``, ``test``.
        """
        import pandas as pd

        # Convert to numpy
        X = features.values if isinstance(features, pd.DataFrame) else np.asarray(features)
        y = targets.values if isinstance(targets, (pd.Series, pd.DataFrame)) else np.asarray(targets)

        # Update input dim from data
        self.config.input_dim = X.shape[1]

        # Split: train+val vs test
        test_ratio = self.config.test_split
        train_val_ratio = 1.0 - test_ratio

        X_train_val, self._X_test, y_train_val, self._y_test = train_test_split(
            X, y, train_size=train_val_ratio, random_state=self.config.random_seed
        )

        # Split train+val into train vs val
        val_ratio_adjusted = self.config.val_split / train_val_ratio
        self._X_train, self._X_val, self._y_train, self._y_val = train_test_split(
            X_train_val, y_train_val,
            test_size=val_ratio_adjusted,
            random_state=self.config.random_seed,
        )

        # Scale features
        self._X_train = self._scaler.fit_transform(self._X_train)
        self._X_val = self._scaler.transform(self._X_val)
        self._X_test = self._scaler.transform(self._X_test)

        # Create data loaders
        self._train_loader = self._make_loader(self._X_train, self._y_train, shuffle=True)
        self._val_loader = self._make_loader(self._X_val, self._y_val, shuffle=False)
        self._test_loader = self._make_loader(self._X_test, self._y_test, shuffle=False)

        sizes = {
            "train": len(self._X_train),
            "val": len(self._X_val),
            "test": len(self._X_test),
        }
        logger.info("Data prepared: train=%d, val=%d, test=%d", sizes["train"], sizes["val"], sizes["test"])
        return sizes

    def build_model(self) -> FinancialNet:
        """Build the PyTorch model according to pipeline configuration.

        Constructs a ``FinancialNet`` with the configured architecture,
        initializes the AdamW optimizer with weight decay, and sets the
        loss criterion (MSE for regression, CrossEntropy for classification).

        Returns
        -------
        FinancialNet
            The constructed neural network model (``nn.Module``).
        """
        self._model = FinancialNet(
            input_dim=self.config.input_dim,
            hidden_dims=self.config.hidden_dims,
            output_dim=self.config.output_dim,
            dropout_rate=self.config.dropout_rate,
            task_type=self.config.task_type,
        ).to(self._device)

        self._optimizer = torch.optim.AdamW(
            self._model.parameters(),
            lr=self.config.learning_rate,
            weight_decay=self.config.weight_decay,
        )

        if self.config.task_type == "regression":
            self._criterion = nn.MSELoss()
        else:
            self._criterion = nn.CrossEntropyLoss()

        total_params = sum(p.numel() for p in self._model.parameters())
        trainable_params = sum(p.numel() for p in self._model.parameters() if p.requires_grad)
        logger.info(
            "Built FinancialNet: %d total params (%d trainable)",
            total_params, trainable_params,
        )
        return self._model

    def train(self) -> dict[str, Any]:
        """Run the training loop with early stopping.

        Trains the model for up to ``config.epochs`` epochs with
        early stopping based on validation loss. Applies gradient
        clipping (max norm 1.0) to stabilize training on noisy
        financial data.

        Returns
        -------
        dict[str, Any]
            Training summary with ``best_epoch``, ``best_val_loss``,
            ``final_train_loss``, ``total_epochs``,
            ``training_time_seconds``, and ``early_stopped``.

        Raises
        ------
        RuntimeError
            If ``prepare_data`` or ``build_model`` has not been called.
        """
        if self._model is None or self._optimizer is None or self._criterion is None:
            raise RuntimeError("Call build_model() before train()")
        if self._train_loader is None or self._val_loader is None:
            raise RuntimeError("Call prepare_data() before train()")

        self._train_losses = []
        self._val_losses = []
        self._best_val_loss = float("inf")
        patience_counter = 0
        best_epoch = 0

        start_time = time.time()

        for epoch in range(1, self.config.epochs + 1):
            # Training phase
            self._model.train()
            train_loss = 0.0
            n_batches = 0

            for X_batch, y_batch in self._train_loader:
                X_batch = X_batch.to(self._device)
                y_batch = y_batch.to(self._device)

                self._optimizer.zero_grad()
                predictions = self._model(X_batch)

                if self.config.task_type == "regression":
                    predictions = predictions.squeeze(-1)

                loss = self._criterion(predictions, y_batch)
                loss.backward()

                # Gradient clipping for stability on noisy financial data
                torch.nn.utils.clip_grad_norm_(self._model.parameters(), max_norm=1.0)

                self._optimizer.step()
                train_loss += loss.item()
                n_batches += 1

            avg_train_loss = train_loss / max(n_batches, 1)
            self._train_losses.append(avg_train_loss)

            # Validation phase
            val_loss = self._validate()
            self._val_losses.append(val_loss)

            # Early stopping check
            if val_loss < self._best_val_loss:
                self._best_val_loss = val_loss
                self._best_model_state = {
                    k: v.clone() for k, v in self._model.state_dict().items()
                }
                patience_counter = 0
                best_epoch = epoch
            else:
                patience_counter += 1

            if epoch % 10 == 0 or epoch == 1:
                logger.info(
                    "Epoch %d/%d - train_loss: %.6f, val_loss: %.6f%s",
                    epoch, self.config.epochs, avg_train_loss, val_loss,
                    " *" if patience_counter == 0 else "",
                )

            if patience_counter >= self.config.early_stopping_patience:
                logger.info("Early stopping triggered at epoch %d (best epoch: %d)", epoch, best_epoch)
                break

        # Restore best model weights
        if self._best_model_state is not None:
            self._model.load_state_dict(self._best_model_state)

        self._training_time = time.time() - start_time

        result = {
            "best_epoch": best_epoch,
            "best_val_loss": self._best_val_loss,
            "final_train_loss": self._train_losses[-1] if self._train_losses else 0.0,
            "total_epochs": len(self._train_losses),
            "training_time_seconds": self._training_time,
            "early_stopped": patience_counter >= self.config.early_stopping_patience,
        }

        logger.info(
            "Training completed: best_epoch=%d, best_val_loss=%.6f, time=%.1fs",
            best_epoch, self._best_val_loss, self._training_time,
        )
        return result

    def evaluate(self) -> dict[str, float]:
        """Evaluate the trained model on the held-out test set.

        Computes regression metrics (MSE, RMSE, MAE, R-squared) or
        classification metrics (accuracy) depending on the task type.
        For regression, also computes financial-specific metrics:

        - **directional_accuracy**: fraction of correctly predicted
          return directions (positive vs negative).
        - **information_coefficient**: Spearman rank correlation between
          predictions and actuals.

        Returns
        -------
        dict[str, float]
            Evaluation metrics on the test set.

        Raises
        ------
        RuntimeError
            If the model has not been trained.
        """
        if self._model is None or self._test_loader is None:
            raise RuntimeError("Model not trained. Call train() first.")

        self._model.eval()
        all_preds: list[np.ndarray] = []
        all_targets: list[np.ndarray] = []

        with torch.no_grad():
            for X_batch, y_batch in self._test_loader:
                X_batch = X_batch.to(self._device)
                predictions = self._model(X_batch)

                if self.config.task_type == "regression":
                    predictions = predictions.squeeze(-1)

                all_preds.append(predictions.cpu().numpy())
                all_targets.append(y_batch.numpy())

        preds = np.concatenate(all_preds)
        targets = np.concatenate(all_targets)

        if self.config.task_type == "regression":
            mse = float(np.mean((preds - targets) ** 2))
            rmse = float(np.sqrt(mse))
            mae = float(np.mean(np.abs(preds - targets)))
            ss_res = float(np.sum((targets - preds) ** 2))
            ss_tot = float(np.sum((targets - np.mean(targets)) ** 2))
            r2 = 1.0 - (ss_res / ss_tot) if ss_tot > 0 else 0.0

            # Directional accuracy (for return prediction)
            if len(preds) > 1:
                pred_direction = np.sign(preds)
                actual_direction = np.sign(targets)
                directional_accuracy = float(np.mean(pred_direction == actual_direction))
            else:
                directional_accuracy = 0.0

            # Information Coefficient (Spearman rank correlation)
            from scipy.stats import spearmanr

            ic, _ = spearmanr(preds, targets)
            ic = float(ic) if not np.isnan(ic) else 0.0

            self._eval_metrics = {
                "test_mse": mse,
                "test_rmse": rmse,
                "test_mae": mae,
                "test_r2": r2,
                "directional_accuracy": directional_accuracy,
                "information_coefficient": ic,
            }
        else:
            pred_labels = np.argmax(preds, axis=1) if preds.ndim > 1 else (preds > 0.5).astype(int)
            accuracy = float(np.mean(pred_labels == targets))
            self._eval_metrics = {"test_accuracy": accuracy}

        logger.info("Evaluation metrics: %s", self._eval_metrics)
        return self._eval_metrics

    def log_to_mlflow(self) -> str:
        """Log the entire pipeline run to MLflow.

        Logs all configuration parameters, per-epoch training and
        validation losses, evaluation metrics, the trained PyTorch model
        artifact, and the fitted ``StandardScaler`` preprocessing artifact.

        Returns
        -------
        str
            MLflow run ID.

        Raises
        ------
        RuntimeError
            If the model has not been trained.
        """
        if self._model is None:
            raise RuntimeError("No model to log. Call train() first.")

        mlflow.set_tracking_uri(self.config.mlflow_tracking_uri)
        mlflow.set_experiment(self.config.experiment_name)

        with mlflow.start_run(run_name=self.config.run_name) as run:
            # Log pipeline configuration
            mlflow.log_params({
                "input_dim": self.config.input_dim,
                "hidden_dims": str(self.config.hidden_dims),
                "output_dim": self.config.output_dim,
                "dropout_rate": self.config.dropout_rate,
                "learning_rate": self.config.learning_rate,
                "weight_decay": self.config.weight_decay,
                "batch_size": self.config.batch_size,
                "epochs": self.config.epochs,
                "early_stopping_patience": self.config.early_stopping_patience,
                "task_type": self.config.task_type,
                "train_split": self.config.train_split,
                "val_split": self.config.val_split,
                "test_split": self.config.test_split,
            })

            # Log training metrics per epoch
            for epoch_idx, (tl, vl) in enumerate(zip(self._train_losses, self._val_losses)):
                mlflow.log_metric("train_loss", tl, step=epoch_idx + 1)
                mlflow.log_metric("val_loss", vl, step=epoch_idx + 1)

            # Log summary metrics
            mlflow.log_metric("best_val_loss", self._best_val_loss)
            mlflow.log_metric("training_time_seconds", self._training_time)
            mlflow.log_metric("total_epochs", len(self._train_losses))

            # Log evaluation metrics
            for key, value in self._eval_metrics.items():
                mlflow.log_metric(key, value)

            # Log data split sizes
            if self._X_train is not None:
                mlflow.log_metric("train_samples", len(self._X_train))
            if self._X_val is not None:
                mlflow.log_metric("val_samples", len(self._X_val))
            if self._X_test is not None:
                mlflow.log_metric("test_samples", len(self._X_test))

            # Log trained PyTorch model artifact
            mlflow.pytorch.log_model(
                self._model,
                artifact_path="model",
                registered_model_name=None,
            )

            # Log preprocessing scaler as artifact
            import os
            import tempfile

            import joblib

            with tempfile.TemporaryDirectory() as tmpdir:
                scaler_path = os.path.join(tmpdir, "scaler.joblib")
                joblib.dump(self._scaler, scaler_path)
                mlflow.log_artifact(scaler_path, artifact_path="preprocessing")

            run_id = run.info.run_id
            logger.info("Logged pipeline run to MLflow (run_id=%s)", run_id)
            return run_id

    def _validate(self) -> float:
        """Run validation pass and return average loss."""
        if self._model is None or self._criterion is None or self._val_loader is None:
            return float("inf")

        self._model.eval()
        val_loss = 0.0
        n_batches = 0

        with torch.no_grad():
            for X_batch, y_batch in self._val_loader:
                X_batch = X_batch.to(self._device)
                y_batch = y_batch.to(self._device)

                predictions = self._model(X_batch)
                if self.config.task_type == "regression":
                    predictions = predictions.squeeze(-1)

                loss = self._criterion(predictions, y_batch)
                val_loss += loss.item()
                n_batches += 1

        return val_loss / max(n_batches, 1)

    def _make_loader(
        self,
        X: np.ndarray,
        y: np.ndarray,
        shuffle: bool = False,
    ) -> DataLoader[Any]:
        """Create a PyTorch DataLoader from numpy arrays."""
        X_tensor = torch.tensor(X, dtype=torch.float32)

        if self.config.task_type == "regression":
            y_tensor = torch.tensor(y, dtype=torch.float32)
        else:
            y_tensor = torch.tensor(y, dtype=torch.long)

        dataset = TensorDataset(X_tensor, y_tensor)
        return DataLoader(
            dataset,
            batch_size=self.config.batch_size,
            shuffle=shuffle,
            drop_last=False,
        )


__all__ = [
    "FinancialNet",
    "MLPipeline",
    "PipelineConfig",
]
