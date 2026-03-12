"""LSTM momentum decomposition model for IDX.

2-layer LSTM that decomposes momentum into persistent vs transient components.
Uses Huber loss for robustness to outliers. Fixed seed (42) for reproducibility.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import numpy as np
import numpy.typing as npt
import pandas as pd
import torch
import torch.nn as nn
from torch.utils.data import DataLoader, Dataset

# Fixed seed for reproducibility
_SEED = 42


@dataclass
class LSTMConfig:
    """Configuration for LSTM momentum model."""

    input_size: int = 10
    hidden_size: int = 64
    num_layers: int = 2
    dropout: float = 0.2
    sequence_length: int = 21  # 1 month of trading days
    learning_rate: float = 1e-3
    batch_size: int = 64
    max_epochs: int = 100
    patience: int = 10
    huber_delta: float = 1.0
    seed: int = _SEED


class MomentumSequenceDataset(Dataset):  # type: ignore[misc]
    """PyTorch Dataset for momentum sequences.

    Each sample is a (sequence_length, n_features) tensor of historical
    feature values for a single security, with label being the forward return.
    """

    def __init__(
        self,
        sequences: npt.NDArray[Any],
        labels: npt.NDArray[Any],
    ) -> None:
        self._sequences = torch.FloatTensor(sequences)
        self._labels = torch.FloatTensor(labels)

    def __len__(self) -> int:
        return len(self._labels)

    def __getitem__(self, idx: int) -> tuple[torch.Tensor, torch.Tensor]:
        return self._sequences[idx], self._labels[idx]


class IDXLSTMMomentumModel(nn.Module):  # type: ignore[misc]
    """2-layer LSTM for momentum decomposition.

    Architecture:
    - Input: (batch, seq_len, n_features)
    - LSTM: 2 layers with dropout
    - FC head: hidden → hidden//2 → 2 outputs
    - Output: (persistent_momentum, transient_momentum)

    The sum of persistent + transient gives total predicted return.
    """

    def __init__(self, config: LSTMConfig | None = None) -> None:
        super().__init__()
        self.config = config or LSTMConfig()

        self.lstm = nn.LSTM(
            input_size=self.config.input_size,
            hidden_size=self.config.hidden_size,
            num_layers=self.config.num_layers,
            dropout=self.config.dropout if self.config.num_layers > 1 else 0.0,
            batch_first=True,
        )

        self.fc = nn.Sequential(
            nn.Linear(self.config.hidden_size, self.config.hidden_size // 2),
            nn.ReLU(),
            nn.Dropout(self.config.dropout),
            nn.Linear(self.config.hidden_size // 2, 2),  # persistent, transient
        )

        self._init_weights()

    def _init_weights(self) -> None:
        """Xavier initialisation for linear layers."""
        for module in self.modules():
            if isinstance(module, nn.Linear):
                nn.init.xavier_uniform_(module.weight)
                if module.bias is not None:
                    nn.init.zeros_(module.bias)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """Forward pass.

        Parameters
        ----------
        x : Tensor of shape (batch, seq_len, n_features)

        Returns
        -------
        Tensor of shape (batch, 2) — [persistent, transient]
        """
        lstm_out, _ = self.lstm(x)
        # Use last hidden state
        last_hidden = lstm_out[:, -1, :]
        return self.fc(last_hidden)

    def predict_alpha(self, x: torch.Tensor) -> torch.Tensor:
        """Return combined alpha signal (persistent + transient)."""
        self.eval()
        with torch.no_grad():
            components = self.forward(x)
            return components.sum(dim=1)

    def decompose(self, x: torch.Tensor) -> tuple[torch.Tensor, torch.Tensor]:
        """Return (persistent, transient) momentum components."""
        self.eval()
        with torch.no_grad():
            components = self.forward(x)
            return components[:, 0], components[:, 1]


class IDXLSTMTrainer:
    """Trainer for the LSTM momentum model.

    Handles data preparation, training loop, early stopping,
    and model serialisation.
    """

    def __init__(self, config: LSTMConfig | None = None) -> None:
        self.config = config or LSTMConfig()
        self._model: IDXLSTMMomentumModel | None = None
        self._train_losses: list[float] = []
        self._val_losses: list[float] = []
        self._best_val_loss: float = float("inf")

    @property
    def model(self) -> IDXLSTMMomentumModel | None:
        return self._model

    @property
    def train_losses(self) -> list[float]:
        return list(self._train_losses)

    @property
    def val_losses(self) -> list[float]:
        return list(self._val_losses)

    def prepare_sequences(
        self,
        features: pd.DataFrame,
        labels: pd.Series,
        sequence_length: int | None = None,
    ) -> tuple[npt.NDArray[Any], npt.NDArray[Any]]:
        """Convert cross-sectional features to LSTM sequences.

        Parameters
        ----------
        features : DataFrame
            MultiIndex (date, symbol) × feature columns.
        labels : Series
            Forward return labels with same index.
        sequence_length : int, optional
            Override config sequence length.

        Returns
        -------
        tuple of (sequences, targets)
            sequences: (n_samples, seq_len, n_features)
            targets: (n_samples,)
        """
        seq_len = sequence_length or self.config.sequence_length

        if isinstance(features.index, pd.MultiIndex):
            dates = features.index.get_level_values(0).unique().sort_values()
            symbols = features.index.get_level_values(1).unique()
        else:
            raise ValueError("Features must have MultiIndex (date, symbol)")

        sequences = []
        targets = []

        for symbol in symbols:
            # Get feature time series for this symbol
            try:
                sym_features = features.xs(symbol, level=1)
                sym_labels = labels.xs(symbol, level=1)
            except KeyError:
                continue

            # Align on common dates
            common_dates = sym_features.index.intersection(sym_labels.index)
            sym_features = sym_features.loc[common_dates]
            sym_labels = sym_labels.loc[common_dates]

            if len(sym_features) < seq_len + 1:
                continue

            values = sym_features.values
            label_values = sym_labels.values

            for i in range(seq_len, len(values)):
                seq = values[i - seq_len : i]
                if not np.isnan(seq).any() and not np.isnan(label_values[i]):
                    sequences.append(seq)
                    targets.append(label_values[i])

        if not sequences:
            return np.array([]).reshape(0, seq_len, features.shape[1]), np.array([])

        return np.array(sequences), np.array(targets)

    def train(
        self,
        X_train: npt.NDArray[Any],
        y_train: npt.NDArray[Any],
        X_val: npt.NDArray[Any] | None = None,
        y_val: npt.NDArray[Any] | None = None,
    ) -> dict[str, Any]:
        """Train the LSTM model.

        Parameters
        ----------
        X_train : ndarray of shape (n_samples, seq_len, n_features)
        y_train : ndarray of shape (n_samples,)
        X_val : ndarray, optional
        y_val : ndarray, optional

        Returns
        -------
        dict with training metrics: final_train_loss, best_val_loss,
            n_epochs, stopped_early.
        """
        torch.manual_seed(self.config.seed)
        np.random.seed(self.config.seed)

        # Update input_size from data
        n_features = X_train.shape[2] if X_train.ndim == 3 else self.config.input_size
        self.config.input_size = n_features

        self._model = IDXLSTMMomentumModel(self.config)
        device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self._model.to(device)

        optimizer = torch.optim.Adam(
            self._model.parameters(),
            lr=self.config.learning_rate,
        )
        criterion = nn.HuberLoss(delta=self.config.huber_delta)

        train_dataset = MomentumSequenceDataset(X_train, y_train)
        train_loader = DataLoader(
            train_dataset,
            batch_size=self.config.batch_size,
            shuffle=True,
        )

        val_loader = None
        if X_val is not None and y_val is not None:
            val_dataset = MomentumSequenceDataset(X_val, y_val)
            val_loader = DataLoader(
                val_dataset,
                batch_size=self.config.batch_size,
                shuffle=False,
            )

        self._train_losses = []
        self._val_losses = []
        self._best_val_loss = float("inf")
        patience_counter = 0
        stopped_early = False

        for epoch in range(self.config.max_epochs):
            # Training
            self._model.train()
            epoch_loss = 0.0
            n_batches = 0

            for batch_x, batch_y in train_loader:
                batch_x = batch_x.to(device)
                batch_y = batch_y.to(device)

                optimizer.zero_grad()
                output = self._model(batch_x)
                # Total return = persistent + transient
                pred = output.sum(dim=1)
                loss = criterion(pred, batch_y)
                loss.backward()
                torch.nn.utils.clip_grad_norm_(self._model.parameters(), max_norm=1.0)
                optimizer.step()

                epoch_loss += loss.item()
                n_batches += 1

            avg_train_loss = epoch_loss / max(n_batches, 1)
            self._train_losses.append(avg_train_loss)

            # Validation
            if val_loader is not None:
                val_loss = self._evaluate(val_loader, criterion, device)
                self._val_losses.append(val_loss)

                if val_loss < self._best_val_loss:
                    self._best_val_loss = val_loss
                    patience_counter = 0
                else:
                    patience_counter += 1
                    if patience_counter >= self.config.patience:
                        stopped_early = True
                        break

        return {
            "final_train_loss": self._train_losses[-1] if self._train_losses else 0.0,
            "best_val_loss": self._best_val_loss,
            "n_epochs": len(self._train_losses),
            "stopped_early": stopped_early,
        }

    def _evaluate(
        self,
        loader: DataLoader,
        criterion: nn.Module,
        device: torch.device,
    ) -> float:
        """Evaluate model on validation set."""
        assert self._model is not None
        self._model.eval()
        total_loss = 0.0
        n_batches = 0

        with torch.no_grad():
            for batch_x, batch_y in loader:
                batch_x = batch_x.to(device)
                batch_y = batch_y.to(device)
                output = self._model(batch_x)
                pred = output.sum(dim=1)
                loss = criterion(pred, batch_y)
                total_loss += loss.item()
                n_batches += 1

        return total_loss / max(n_batches, 1)

    def predict(self, X: npt.NDArray[Any]) -> npt.NDArray[Any]:
        """Generate predictions from sequences.

        Parameters
        ----------
        X : ndarray of shape (n_samples, seq_len, n_features)

        Returns
        -------
        ndarray of shape (n_samples,) — combined alpha signal.
        """
        if self._model is None:
            raise RuntimeError("Model not trained. Call train() first.")

        device = next(self._model.parameters()).device
        self._model.eval()

        with torch.no_grad():
            tensor = torch.FloatTensor(X).to(device)
            output = self._model(tensor)
            result: npt.NDArray[Any] = output.sum(dim=1).cpu().numpy()
            return result

    def decompose(self, X: npt.NDArray[Any]) -> tuple[npt.NDArray[Any], npt.NDArray[Any]]:
        """Decompose into persistent and transient momentum.

        Returns
        -------
        tuple of (persistent, transient) ndarrays.
        """
        if self._model is None:
            raise RuntimeError("Model not trained.")

        device = next(self._model.parameters()).device
        self._model.eval()

        with torch.no_grad():
            tensor = torch.FloatTensor(X).to(device)
            output = self._model(tensor)
            persistent = output[:, 0].cpu().numpy()
            transient = output[:, 1].cpu().numpy()
            return persistent, transient

    def save(self, path: str | Path) -> None:
        """Save model state dict and config."""
        if self._model is None:
            raise RuntimeError("No model to save.")
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        torch.save(
            {
                "model_state_dict": self._model.state_dict(),
                "config": self.config,
                "train_losses": self._train_losses,
                "val_losses": self._val_losses,
            },
            path,
        )

    def load(self, path: str | Path) -> None:
        """Load model from checkpoint."""
        checkpoint = torch.load(path, weights_only=False)
        self.config = checkpoint["config"]
        self._model = IDXLSTMMomentumModel(self.config)
        self._model.load_state_dict(checkpoint["model_state_dict"])
        self._train_losses = checkpoint.get("train_losses", [])
        self._val_losses = checkpoint.get("val_losses", [])
