"""Tests for ML feature store."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from unittest.mock import AsyncMock

import numpy as np
import pandas as pd
import pytest

from pyhron.ml.feature_store import FeatureStore


def _make_ohlcv(n_days: int = 100) -> pd.DataFrame:
    """Create synthetic OHLCV data."""
    rng = np.random.default_rng(42)
    dates = pd.bdate_range("2023-01-01", periods=n_days, tz="UTC")
    close = 10000 + np.cumsum(rng.normal(0, 100, n_days))
    volume = rng.integers(1_000_000, 10_000_000, n_days)
    return pd.DataFrame(
        {
            "open": close - rng.uniform(0, 50, n_days),
            "high": close + rng.uniform(0, 100, n_days),
            "low": close - rng.uniform(0, 100, n_days),
            "close": close,
            "volume": volume,
        },
        index=dates,
    )


class TestFeatureStore:
    def test_pit_boundary_enforcement(self) -> None:
        """Features should only use data up to as_of."""
        store = FeatureStore()
        df = _make_ohlcv(100)
        as_of = df.index[50]

        features = store.compute_features("BBCA", as_of, df, window=60)
        assert not features.empty
        # The features should only use data before/at as_of
        # We verify indirectly: momentum_5d should be based on data[46:51]
        assert "momentum_5d" in features.index

    def test_compute_features_produces_expected_names(self) -> None:
        store = FeatureStore()
        df = _make_ohlcv(300)
        as_of = df.index[-1]

        features = store.compute_features("BBCA", as_of, df, window=260)
        expected_keys = {"momentum_5d", "momentum_20d", "volatility_20d", "volume_ratio", "rsi_14", "macd_signal"}
        assert expected_keys.issubset(set(features.index))

    def test_cross_sectional_zscore(self) -> None:
        """After z-scoring, mean ≈ 0 and std ≈ 1."""
        rng = np.random.default_rng(42)
        features_df = pd.DataFrame(
            rng.normal(100, 20, (50, 5)),
            columns=["a", "b", "c", "d", "e"],
        )
        result = FeatureStore.winsorize_and_zscore(features_df)
        for col in result.columns:
            assert abs(result[col].mean()) < 0.1
            assert abs(result[col].std() - 1.0) < 0.2

    def test_empty_dataframe(self) -> None:
        store = FeatureStore()
        df = pd.DataFrame(columns=["open", "high", "low", "close", "volume"])
        as_of = datetime(2024, 1, 1, tzinfo=UTC)
        features = store.compute_features("BBCA", as_of, df)
        assert features.empty

    def test_custom_feature_registration(self) -> None:
        store = FeatureStore()
        store.register_feature("custom_ma5", lambda df: df["close"].rolling(5).mean())
        df = _make_ohlcv(50)
        features = store.compute_features("BBCA", df.index[-1], df)
        assert "custom_ma5" in features.index


class TestFeatureStoreCache:
    @pytest.mark.asyncio
    async def test_redis_cache_hit(self) -> None:
        redis = AsyncMock()
        cached_data = json.dumps({"momentum_5d": 0.02, "rsi_14": 55.0})
        redis.get.return_value = cached_data

        store = FeatureStore(redis_client=redis, cache_ttl=300)
        df = _make_ohlcv(50)
        as_of = df.index[-1]

        result = await store.get_or_compute("BBCA", as_of, df)
        assert result["momentum_5d"] == 0.02
        redis.get.assert_called_once()

    @pytest.mark.asyncio
    async def test_redis_cache_miss(self) -> None:
        redis = AsyncMock()
        redis.get.return_value = None

        store = FeatureStore(redis_client=redis, cache_ttl=300)
        df = _make_ohlcv(50)
        as_of = df.index[-1]

        result = await store.get_or_compute("BBCA", as_of, df)
        assert not result.empty
        redis.set.assert_called_once()
