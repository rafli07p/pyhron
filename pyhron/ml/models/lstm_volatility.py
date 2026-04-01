"""LSTM volatility forecaster (1-day-ahead realized vol).

Architecture: LSTM(hidden=64, layers=2) → Linear(1) → ReLU.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import TYPE_CHECKING, Any

import numpy as np

if TYPE_CHECKING:
    import pandas as pd

logger = logging.getLogger(__name__)

_SEQUENCE_LENGTH = 20
_HIDDEN_SIZE = 64
_NUM_LAYERS = 2
_FEATURE_COLS = ["log_ret", "volume_ratio", "rsi_14", "macd_signal"]


class LSTMVolatilityModel:
    """LSTM model for 1-day-ahead realised volatility forecasting.

    Parameters
    ----------
    hidden_size:
        LSTM hidden dimension.
    num_layers:
        Number of stacked LSTM layers.
    sequence_length:
        Input sequence length in days.
    learning_rate:
        Adam learning rate.
    max_epochs:
        Maximum training epochs.
    patience:
        Early stopping patience.
    """

    def __init__(
        self,
        hidden_size: int = _HIDDEN_SIZE,
        num_layers: int = _NUM_LAYERS,
        sequence_length: int = _SEQUENCE_LENGTH,
        learning_rate: float = 1e-3,
        max_epochs: int = 100,
        patience: int = 10,
    ) -> None:
        self._hidden_size = hidden_size
        self._num_layers = num_layers
        self._seq_len = sequence_length
        self._lr = learning_rate
        self._max_epochs = max_epochs
        self._patience = patience
        self._model: Any = None
        self._scaler_mean: np.ndarray | None = None
        self._scaler_std: np.ndarray | None = None

    def _build_model(self, input_size: int) -> Any:
        """Build the PyTorch LSTM model."""
        import torch
        import torch.nn as nn

        class _VolLSTM(nn.Module):
            def __init__(self, input_size: int, hidden_size: int, num_layers: int) -> None:
                super().__init__()
                self.lstm = nn.LSTM(
                    input_size=input_size,
                    hidden_size=hidden_size,
                    num_layers=num_layers,
                    batch_first=True,
                    dropout=0.1 if num_layers > 1 else 0.0,
                )
                self.fc = nn.Linear(hidden_size, 1)
                self.relu = nn.ReLU()

            def forward(self, x: torch.Tensor) -> torch.Tensor:
                lstm_out, _ = self.lstm(x)
                last_hidden = lstm_out[:, -1, :]
                return self.relu(self.fc(last_hidden))

        return _VolLSTM(input_size, self._hidden_size, self._num_layers)

    def _prepare_sequences(
        self,
        features: np.ndarray,
        targets: np.ndarray | None = None,
    ) -> tuple[np.ndarray, np.ndarray | None]:
        """Create windowed sequences."""
        X_list = []
        y_list = [] if targets is not None else None

        for i in range(self._seq_len, len(features)):
            X_list.append(features[i - self._seq_len : i])
            if targets is not None and y_list is not None:
                y_list.append(targets[i])

        X = np.array(X_list)
        y = np.array(y_list) if y_list is not None else None
        return X, y

    def fit(
        self,
        features_df: pd.DataFrame,
        target: pd.Series,
    ) -> dict[str, float]:
        """Train the LSTM model.

        Parameters
        ----------
        features_df:
            DataFrame with feature columns.
        target:
            Next-day realised volatility target.

        Returns
        -------
        dict
            Training metrics (final_loss, best_loss).
        """
        import torch
        import torch.nn as nn

        # Normalise features
        values = features_df.values.astype(np.float32)
        self._scaler_mean = values.mean(axis=0)
        self._scaler_std = values.std(axis=0) + 1e-8
        normalised = (values - self._scaler_mean) / self._scaler_std

        target_arr = target.values.astype(np.float32)

        X_np, y_np = self._prepare_sequences(normalised, target_arr)
        if X_np is None or y_np is None or len(X_np) < 10:
            msg = "Insufficient data for LSTM training"
            raise ValueError(msg)

        X_t = torch.from_numpy(X_np)
        y_t = torch.from_numpy(y_np).unsqueeze(1)

        # Train/validation split
        split = int(0.8 * len(X_t))
        X_train, X_val = X_t[:split], X_t[split:]
        y_train, y_val = y_t[:split], y_t[split:]

        self._model = self._build_model(X_np.shape[2])
        optimizer = torch.optim.Adam(self._model.parameters(), lr=self._lr)
        criterion = nn.MSELoss()

        best_val_loss = float("inf")
        patience_counter = 0

        for epoch in range(self._max_epochs):
            self._model.train()
            optimizer.zero_grad()
            pred = self._model(X_train)
            loss = criterion(pred, y_train)
            loss.backward()
            optimizer.step()

            # Validation
            self._model.eval()
            with torch.no_grad():
                val_pred = self._model(X_val)
                val_loss = criterion(val_pred, y_val).item()

            if val_loss < best_val_loss:
                best_val_loss = val_loss
                patience_counter = 0
            else:
                patience_counter += 1

            if patience_counter >= self._patience:
                logger.info(
                    "lstm_early_stop",
                    extra={"epoch": epoch, "val_loss": val_loss},
                )
                break

        return {"final_loss": loss.item(), "best_val_loss": best_val_loss}

    def predict(self, features_df: pd.DataFrame) -> float:
        """Predict 1-day-ahead volatility.

        Parameters
        ----------
        features_df:
            Recent feature values (at least ``sequence_length`` rows).

        Returns
        -------
        float
            Predicted realised volatility.
        """
        if self._model is None:
            msg = "Model not trained"
            raise RuntimeError(msg)

        import torch

        values = features_df.values.astype(np.float32)
        assert self._scaler_mean is not None
        assert self._scaler_std is not None
        normalised = (values - self._scaler_mean) / self._scaler_std

        X_np, _ = self._prepare_sequences(normalised)
        if len(X_np) == 0:
            return 0.0

        X_t = torch.from_numpy(X_np[-1:])
        self._model.eval()
        with torch.no_grad():
            pred = self._model(X_t)
        return float(pred.item())

    def export_onnx(self, path: Path) -> None:
        """Export model to ONNX format."""
        if self._model is None:
            msg = "Model not trained"
            raise RuntimeError(msg)

        import torch

        self._model.eval()
        dummy = torch.randn(1, self._seq_len, 4)
        torch.onnx.export(
            self._model,
            dummy,
            str(path),
            input_names=["features"],
            output_names=["volatility"],
            dynamic_axes={"features": {0: "batch_size"}},
        )
        logger.info("lstm_exported_onnx path=%s", path)
