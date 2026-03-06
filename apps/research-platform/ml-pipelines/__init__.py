"""ML training pipelines with PyTorch and MLflow tracking.

Provides end-to-end pipelines for training, evaluating, and registering
quantitative ML models with full experiment tracking.
"""

from __future__ import annotations

from typing import Any

import mlflow
import numpy as np
import pandas as pd
import structlog
import torch
import torch.nn as nn
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from torch.utils.data import DataLoader, TensorDataset

logger = structlog.get_logger(__name__)


class AlphaNet(nn.Module):
    """Simple feedforward network for alpha signal prediction."""

    def __init__(self, input_dim: int, hidden_dim: int = 128, dropout: float = 0.3):
        super().__init__()
        self.net = nn.Sequential(
            nn.Linear(input_dim, hidden_dim),
            nn.BatchNorm1d(hidden_dim),
            nn.ReLU(),
            nn.Dropout(dropout),
            nn.Linear(hidden_dim, hidden_dim // 2),
            nn.BatchNorm1d(hidden_dim // 2),
            nn.ReLU(),
            nn.Dropout(dropout),
            nn.Linear(hidden_dim // 2, 1),
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.net(x)


class MLPipeline:
    """End-to-end ML pipeline with MLflow experiment tracking."""

    def __init__(
        self,
        experiment_name: str = "enthropy-alpha",
        tracking_uri: str | None = None,
    ):
        self.experiment_name = experiment_name
        self.scaler = StandardScaler()
        self.model: AlphaNet | None = None
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

        if tracking_uri:
            mlflow.set_tracking_uri(tracking_uri)
        mlflow.set_experiment(experiment_name)

    def prepare_data(
        self,
        df: pd.DataFrame,
        target_col: str = "forward_return",
        test_size: float = 0.2,
        batch_size: int = 256,
    ) -> tuple[DataLoader, DataLoader, int]:
        """Prepare data for training with proper scaling and splitting."""
        feature_cols = [c for c in df.columns if c != target_col]
        X = df[feature_cols].values.astype(np.float32)
        y = df[target_col].values.astype(np.float32).reshape(-1, 1)

        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=test_size, shuffle=False
        )

        X_train = self.scaler.fit_transform(X_train).astype(np.float32)
        X_test = self.scaler.transform(X_test).astype(np.float32)

        train_ds = TensorDataset(
            torch.from_numpy(X_train), torch.from_numpy(y_train)
        )
        test_ds = TensorDataset(
            torch.from_numpy(X_test), torch.from_numpy(y_test)
        )

        train_loader = DataLoader(train_ds, batch_size=batch_size, shuffle=True)
        test_loader = DataLoader(test_ds, batch_size=batch_size)

        return train_loader, test_loader, X_train.shape[1]

    def build_model(self, input_dim: int, hidden_dim: int = 128) -> AlphaNet:
        self.model = AlphaNet(input_dim, hidden_dim).to(self.device)
        return self.model

    def train(
        self,
        train_loader: DataLoader,
        test_loader: DataLoader,
        epochs: int = 50,
        lr: float = 1e-3,
        params: dict[str, Any] | None = None,
    ) -> dict[str, float]:
        """Train model with MLflow tracking."""
        if self.model is None:
            raise RuntimeError("Call build_model first")

        optimizer = torch.optim.Adam(self.model.parameters(), lr=lr)
        criterion = nn.MSELoss()

        with mlflow.start_run():
            mlflow.log_params(
                {"epochs": epochs, "lr": lr, "hidden_dim": 128, **(params or {})}
            )

            best_loss = float("inf")
            for epoch in range(epochs):
                self.model.train()
                train_loss = 0.0
                for X_batch, y_batch in train_loader:
                    X_batch = X_batch.to(self.device)
                    y_batch = y_batch.to(self.device)

                    optimizer.zero_grad()
                    pred = self.model(X_batch)
                    loss = criterion(pred, y_batch)
                    loss.backward()
                    optimizer.step()
                    train_loss += loss.item()

                train_loss /= len(train_loader)
                val_metrics = self.evaluate(test_loader)

                mlflow.log_metrics(
                    {"train_loss": train_loss, **val_metrics}, step=epoch
                )

                if val_metrics["val_loss"] < best_loss:
                    best_loss = val_metrics["val_loss"]

                if (epoch + 1) % 10 == 0:
                    logger.info(
                        "training_progress",
                        epoch=epoch + 1,
                        train_loss=round(train_loss, 6),
                        val_loss=round(val_metrics["val_loss"], 6),
                    )

            mlflow.pytorch.log_model(self.model, "model")
            return {"best_val_loss": best_loss, **val_metrics}

    def evaluate(self, loader: DataLoader) -> dict[str, float]:
        if self.model is None:
            raise RuntimeError("No model to evaluate")

        self.model.eval()
        total_loss = 0.0
        predictions, actuals = [], []
        criterion = nn.MSELoss()

        with torch.no_grad():
            for X_batch, y_batch in loader:
                X_batch = X_batch.to(self.device)
                y_batch = y_batch.to(self.device)
                pred = self.model(X_batch)
                total_loss += criterion(pred, y_batch).item()
                predictions.extend(pred.cpu().numpy().flatten())
                actuals.extend(y_batch.cpu().numpy().flatten())

        preds = np.array(predictions)
        acts = np.array(actuals)
        correlation = float(np.corrcoef(preds, acts)[0, 1]) if len(preds) > 1 else 0.0

        return {
            "val_loss": total_loss / len(loader),
            "correlation": correlation,
        }

    def log_to_mlflow(self, metrics: dict[str, float], artifacts: dict[str, str] | None = None) -> None:
        with mlflow.start_run():
            mlflow.log_metrics(metrics)
            if artifacts:
                for name, path in artifacts.items():
                    mlflow.log_artifact(path, name)
