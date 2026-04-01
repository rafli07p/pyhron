"""Feature store backed by Redis for ML signal generation.

Computes and caches cross-sectional equity features with strict
point-in-time boundaries to prevent look-ahead bias.
"""

from __future__ import annotations

import json
import logging
from collections.abc import Callable
from datetime import UTC, datetime
from typing import Any

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


class FeatureStore:
    """Feature computation and caching backed by Redis.

    All features are computed with strict ``as_of`` PIT boundaries.
    Results are cached in Redis with a configurable TTL.

    Parameters
    ----------
    redis_client:
        Async Redis client instance.
    cache_ttl:
        Cache TTL in seconds (default 300).
    """

    def __init__(self, redis_client: Any = None, cache_ttl: int = 300) -> None:
        self._redis = redis_client
        self._cache_ttl = cache_ttl
        self._custom_features: dict[str, Callable[[pd.DataFrame], pd.Series]] = {}

    def register_feature(
        self,
        name: str,
        fn: Callable[[pd.DataFrame], pd.Series],
    ) -> None:
        """Register a custom feature computation function."""
        self._custom_features[name] = fn

    def compute_features(
        self,
        symbol: str,
        as_of: datetime,
        ohlcv_df: pd.DataFrame,
        window: int = 60,
    ) -> pd.Series:
        """Compute all features for a symbol at a point in time.

        Parameters
        ----------
        symbol:
            Ticker symbol.
        as_of:
            Point-in-time boundary.
        ohlcv_df:
            Historical OHLCV data (must be pre-filtered to ``<= as_of``).
        window:
            Lookback window in days.

        Returns
        -------
        pd.Series
            Named feature values.
        """
        if as_of.tzinfo is None:
            as_of = as_of.replace(tzinfo=UTC)

        # Filter to as_of boundary
        if isinstance(ohlcv_df.index, pd.DatetimeIndex):
            if ohlcv_df.index.tz is None:
                ohlcv_df.index = ohlcv_df.index.tz_localize("UTC")
            df = ohlcv_df[ohlcv_df.index <= as_of].tail(window)
        else:
            df = ohlcv_df.tail(window)

        if df.empty or len(df) < 5:
            return pd.Series(dtype=float)

        close = df["close"].astype(float)
        volume = df["volume"].astype(float)
        log_returns = np.log(close / close.shift(1)).dropna()

        features: dict[str, float] = {}

        # Momentum
        if len(close) >= 5:
            features["momentum_5d"] = float(np.log(close.iloc[-1] / close.iloc[-5]))
        if len(close) >= 20:
            features["momentum_20d"] = float(np.log(close.iloc[-1] / close.iloc[-20]))

        # Volatility
        if len(log_returns) >= 20:
            features["volatility_20d"] = float(log_returns.tail(20).std())

        # Volume ratio
        adv20 = volume.tail(20).mean()
        if adv20 > 0:
            features["volume_ratio"] = float(volume.iloc[-1] / adv20)

        # RSI-14
        if len(log_returns) >= 14:
            features["rsi_14"] = self._compute_rsi(close, 14)

        # MACD signal
        if len(close) >= 26:
            features["macd_signal"] = self._compute_macd_signal(close)

        # Price to 52-week high
        if len(close) >= 252:
            rolling_max = close.tail(252).max()
            features["price_to_52w_high"] = float(close.iloc[-1] / rolling_max) if rolling_max > 0 else 0.0
        elif len(close) > 0:
            rolling_max = close.max()
            features["price_to_52w_high"] = float(close.iloc[-1] / rolling_max) if rolling_max > 0 else 0.0

        # Amihud illiquidity
        if len(log_returns) >= 5 and len(volume) >= 5:
            recent_ret = log_returns.tail(20)
            recent_vol = volume.tail(20)
            nonzero_vol = recent_vol[recent_vol > 0]
            if len(nonzero_vol) > 0:
                amihud = (recent_ret.abs() / nonzero_vol).mean()
                features["illiquidity_amihud"] = float(amihud) if np.isfinite(amihud) else 0.0

        # Custom features
        for name, fn in self._custom_features.items():
            try:
                val = fn(df)
                if isinstance(val, pd.Series) and len(val) > 0:
                    features[name] = float(val.iloc[-1])
            except Exception:
                logger.debug("custom_feature_failed name=%s", name)

        return pd.Series(features, dtype=float)

    async def get_or_compute(
        self,
        symbol: str,
        as_of: datetime,
        ohlcv_df: pd.DataFrame,
        window: int = 60,
    ) -> pd.Series:
        """Retrieve features from Redis cache, computing if absent.

        Parameters
        ----------
        symbol:
            Ticker symbol.
        as_of:
            Point-in-time boundary.
        ohlcv_df:
            Historical OHLCV data.
        window:
            Lookback window in days.

        Returns
        -------
        pd.Series
            Cached or freshly computed features.
        """
        cache_key = self._cache_key(symbol, as_of)

        if self._redis is not None:
            try:
                cached = await self._redis.get(cache_key)
                if cached is not None:
                    data = json.loads(cached)
                    return pd.Series(data, dtype=float)
            except Exception:
                logger.debug("redis_cache_miss symbol=%s", symbol)

        features = self.compute_features(symbol, as_of, ohlcv_df, window)

        if self._redis is not None and not features.empty:
            try:
                await self._redis.set(
                    cache_key,
                    features.to_json(),
                    ex=self._cache_ttl,
                )
            except Exception:
                logger.debug("redis_cache_set_failed symbol=%s", symbol)

        return features

    @staticmethod
    def winsorize_and_zscore(
        features_df: pd.DataFrame,
        lower_pct: float = 0.01,
        upper_pct: float = 0.99,
    ) -> pd.DataFrame:
        """Cross-sectionally winsorize and z-score a feature matrix.

        Parameters
        ----------
        features_df:
            DataFrame with (symbols × features).
        lower_pct:
            Lower percentile for winsorization.
        upper_pct:
            Upper percentile for winsorization.

        Returns
        -------
        pd.DataFrame
            Winsorized and z-scored features.
        """
        result = features_df.copy()
        for col in result.columns:
            series = result[col].dropna()
            if len(series) < 2:
                continue
            lo = series.quantile(lower_pct)
            hi = series.quantile(upper_pct)
            result[col] = result[col].clip(lo, hi)
            mean = result[col].mean()
            std = result[col].std()
            if std > 0:
                result[col] = (result[col] - mean) / std
        return result

    @staticmethod
    def _compute_rsi(close: pd.Series, period: int = 14) -> float:
        """Wilder RSI."""
        delta = close.diff()
        gain = delta.where(delta > 0, 0.0)
        loss = (-delta).where(delta < 0, 0.0)
        avg_gain = gain.ewm(alpha=1.0 / period, min_periods=period).mean().iloc[-1]
        avg_loss = loss.ewm(alpha=1.0 / period, min_periods=period).mean().iloc[-1]
        if avg_loss == 0:
            return 100.0
        rs = avg_gain / avg_loss
        return float(100.0 - 100.0 / (1.0 + rs))

    @staticmethod
    def _compute_macd_signal(close: pd.Series) -> float:
        """MACD(12,26,9) signal line value."""
        ema12 = close.ewm(span=12).mean()
        ema26 = close.ewm(span=26).mean()
        macd_line = ema12 - ema26
        signal = macd_line.ewm(span=9).mean()
        return float(signal.iloc[-1])

    @staticmethod
    def _cache_key(symbol: str, as_of: datetime) -> str:
        ts = as_of.isoformat()
        return f"pyhron:features:{symbol}:{ts}"
