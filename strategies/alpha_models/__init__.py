"""Enthropy Alpha Model Framework.

Provides abstract and concrete alpha models for systematic signal
generation.  Includes momentum, mean-reversion, and ML-based models
with Fernet encryption support for IP protection of trained models.

Alpha models consume market data (typically pandas DataFrames of
OHLCV bars) and produce a signal in [-1.0, +1.0] where positive
values indicate bullish conviction and negative values indicate
bearish conviction.
"""

from __future__ import annotations

import io
import pickle  # noqa: S403
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

import numpy as np
import pandas as pd
import structlog
from cryptography.fernet import Fernet
from pydantic import BaseModel, Field

logger = structlog.stdlib.get_logger(__name__)


# ---------------------------------------------------------------------------
# Signal schema
# ---------------------------------------------------------------------------

class AlphaSignal(BaseModel):
    """Output of an alpha model for a single symbol."""

    model_config = {"frozen": True}

    symbol: str
    signal: float = Field(..., ge=-1.0, le=1.0, description="Signal strength [-1, +1]")
    confidence: float = Field(default=1.0, ge=0.0, le=1.0, description="Model confidence")
    model_name: str = ""
    timestamp: datetime = Field(default_factory=lambda: datetime.now(tz=timezone.utc))
    metadata: dict[str, Any] = Field(default_factory=dict)


# ---------------------------------------------------------------------------
# Base alpha model
# ---------------------------------------------------------------------------

class BaseAlphaModel(ABC):
    """Abstract base class for all alpha models.

    Subclasses must implement ``generate_signal`` which receives a
    pandas DataFrame of market data and returns a signal in [-1, +1].
    """

    name: str = "base"

    @abstractmethod
    def generate_signal(self, data: pd.DataFrame) -> float:
        """Produce a directional signal from market data.

        Parameters
        ----------
        data:
            DataFrame with at minimum columns ``open``, ``high``,
            ``low``, ``close``, ``volume`` indexed by datetime.

        Returns
        -------
        float
            Signal in [-1.0, +1.0].
        """
        ...

    def generate_alpha_signal(self, symbol: str, data: pd.DataFrame) -> AlphaSignal:
        """Convenience wrapper that returns a full ``AlphaSignal``."""
        raw = self.generate_signal(data)
        signal = float(np.clip(raw, -1.0, 1.0))
        return AlphaSignal(symbol=symbol, signal=signal, model_name=self.name)

    def __repr__(self) -> str:
        return f"<{type(self).__name__} name={self.name!r}>"


# ---------------------------------------------------------------------------
# Momentum alpha
# ---------------------------------------------------------------------------

class MomentumAlpha(BaseAlphaModel):
    """Momentum-based alpha using rolling returns.

    Computes the annualised return over a lookback window, then maps
    it to [-1, +1] via a scaled tanh transform.

    Parameters
    ----------
    lookback:
        Number of bars for the momentum window (default 20).
    scale:
        Scaling factor for tanh normalisation (default 10.0).
    """

    name: str = "momentum"

    def __init__(self, lookback: int = 20, scale: float = 10.0) -> None:
        self.lookback = lookback
        self.scale = scale

    def generate_signal(self, data: pd.DataFrame) -> float:
        if len(data) < self.lookback + 1:
            return 0.0

        closes = data["close"].astype(float).values
        returns = (closes[-1] / closes[-self.lookback] - 1.0) if closes[-self.lookback] != 0 else 0.0

        # Annualise (assume ~252 trading days, bars may be intraday)
        ann_factor = 252.0 / self.lookback
        ann_return = returns * ann_factor

        signal = float(np.tanh(ann_return * self.scale))
        return signal


# ---------------------------------------------------------------------------
# Mean reversion alpha
# ---------------------------------------------------------------------------

class MeanReversionAlpha(BaseAlphaModel):
    """Mean-reversion alpha using z-score of price relative to moving average.

    A positive z-score (price above mean) produces a negative
    (sell) signal and vice-versa — classic mean-reversion logic.

    Parameters
    ----------
    lookback:
        Rolling window for mean and standard deviation (default 20).
    entry_z:
        Z-score threshold beyond which the signal saturates at +/-1
        (default 2.0).
    """

    name: str = "mean_reversion"

    def __init__(self, lookback: int = 20, entry_z: float = 2.0) -> None:
        self.lookback = lookback
        self.entry_z = entry_z

    def generate_signal(self, data: pd.DataFrame) -> float:
        if len(data) < self.lookback:
            return 0.0

        closes = data["close"].astype(float).values[-self.lookback :]
        mean = float(np.mean(closes))
        std = float(np.std(closes, ddof=1))

        if std < 1e-12:
            return 0.0

        z_score = (closes[-1] - mean) / std

        # Invert: high z -> sell signal (negative), low z -> buy signal
        raw = -z_score / self.entry_z
        return float(np.clip(raw, -1.0, 1.0))


# ---------------------------------------------------------------------------
# ML alpha (MLflow integration)
# ---------------------------------------------------------------------------

class MLAlpha(BaseAlphaModel):
    """ML-based alpha model loaded from MLflow model registry.

    Loads a scikit-learn or PyTorch model from MLflow using the
    specified ``model_uri`` (e.g. ``"models:/my_model/Production"``).
    Falls back to a local pickle file if MLflow is unavailable.

    The model's ``predict`` method should accept a 2-D numpy array of
    features and return a 1-D array of raw predictions which are then
    normalised to [-1, +1] via tanh.

    Parameters
    ----------
    model_uri:
        MLflow model URI, e.g. ``"models:/alpha_v3/Production"``.
    feature_columns:
        Column names to extract from the input DataFrame as features.
    local_path:
        Optional path to a local pickle fallback.
    """

    name: str = "ml_alpha"

    def __init__(
        self,
        model_uri: str = "models:/alpha_v1/Production",
        feature_columns: Optional[list[str]] = None,
        local_path: Optional[str] = None,
    ) -> None:
        self.model_uri = model_uri
        self.feature_columns = feature_columns or [
            "returns_1d",
            "returns_5d",
            "returns_20d",
            "volatility_20d",
            "volume_ratio",
        ]
        self.local_path = local_path
        self._model: Any = None

    def _load_model(self) -> Any:
        """Load model from MLflow or local fallback."""
        if self._model is not None:
            return self._model

        # Try MLflow first
        try:
            import mlflow.pyfunc

            self._model = mlflow.pyfunc.load_model(self.model_uri)
            logger.info("ml_model_loaded", source="mlflow", uri=self.model_uri)
            return self._model
        except Exception:
            logger.warning("mlflow_load_failed", uri=self.model_uri)

        # Fallback to local pickle
        if self.local_path and Path(self.local_path).exists():
            with open(self.local_path, "rb") as f:  # noqa: PTH123
                self._model = pickle.load(f)  # noqa: S301
            logger.info("ml_model_loaded", source="local", path=self.local_path)
            return self._model

        logger.error("ml_model_unavailable", uri=self.model_uri, local_path=self.local_path)
        return None

    def _engineer_features(self, data: pd.DataFrame) -> np.ndarray:
        """Compute standard quant features from OHLCV data."""
        df = data.copy()
        close = df["close"].astype(float)
        volume = df["volume"].astype(float)

        df["returns_1d"] = close.pct_change(1)
        df["returns_5d"] = close.pct_change(5)
        df["returns_20d"] = close.pct_change(20)
        df["volatility_20d"] = close.pct_change().rolling(20).std()
        df["volume_ratio"] = volume / volume.rolling(20).mean()

        # Use only the columns the model expects, take the last row
        available = [c for c in self.feature_columns if c in df.columns]
        features = df[available].iloc[-1:].fillna(0).values
        return features

    def generate_signal(self, data: pd.DataFrame) -> float:
        if len(data) < 25:
            return 0.0

        model = self._load_model()
        if model is None:
            return 0.0

        features = self._engineer_features(data)

        try:
            prediction = model.predict(features)
            raw = float(prediction[0]) if hasattr(prediction, "__len__") else float(prediction)
        except Exception:
            logger.exception("ml_predict_error")
            return 0.0

        return float(np.tanh(raw))


# ---------------------------------------------------------------------------
# Model encryption utilities (IP protection)
# ---------------------------------------------------------------------------

def generate_encryption_key() -> bytes:
    """Generate a new Fernet encryption key."""
    return Fernet.generate_key()


def encrypt_model(model: Any, key: bytes) -> bytes:
    """Serialize and encrypt a Python model object using Fernet.

    Parameters
    ----------
    model:
        Any picklable Python object (sklearn model, PyTorch state dict, etc.).
    key:
        Fernet encryption key (32-byte base64-encoded).

    Returns
    -------
    bytes
        Encrypted ciphertext.
    """
    buf = io.BytesIO()
    pickle.dump(model, buf)
    plaintext = buf.getvalue()
    fernet = Fernet(key)
    return fernet.encrypt(plaintext)


def decrypt_model(ciphertext: bytes, key: bytes) -> Any:
    """Decrypt and deserialize a model encrypted with ``encrypt_model``.

    Parameters
    ----------
    ciphertext:
        Encrypted bytes produced by ``encrypt_model``.
    key:
        Same Fernet key used for encryption.

    Returns
    -------
    object
        The original Python model object.
    """
    fernet = Fernet(key)
    plaintext = fernet.decrypt(ciphertext)
    return pickle.loads(plaintext)  # noqa: S301


def save_encrypted_model(model: Any, key: bytes, path: str | Path) -> None:
    """Encrypt a model and write to disk."""
    ciphertext = encrypt_model(model, key)
    Path(path).write_bytes(ciphertext)
    logger.info("model_encrypted_and_saved", path=str(path), size_bytes=len(ciphertext))


def load_encrypted_model(key: bytes, path: str | Path) -> Any:
    """Read an encrypted model file and decrypt it."""
    ciphertext = Path(path).read_bytes()
    model = decrypt_model(ciphertext, key)
    logger.info("model_loaded_and_decrypted", path=str(path))
    return model


__all__ = [
    "AlphaSignal",
    "BaseAlphaModel",
    "MomentumAlpha",
    "MeanReversionAlpha",
    "MLAlpha",
    "generate_encryption_key",
    "encrypt_model",
    "decrypt_model",
    "save_encrypted_model",
    "load_encrypted_model",
]
