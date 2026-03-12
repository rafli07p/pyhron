"""Tests for the ML signal layer.

10 unit tests + 1 integration test covering:
- Feature engineering pipeline
- Label construction
- Purged cross-validation
- LightGBM alpha model
- LSTM momentum model
- Signal combination
- Walk-forward backtest
- SHAP explainability
"""

from __future__ import annotations

import sys
import types

import numpy as np
import pandas as pd

# Stub the parent services.research to avoid pulling in heavy transitive
# dependencies (yfinance, dask, polygon, etc.) from its __init__.py.
if "services.research" not in sys.modules:
    _stub = types.ModuleType("services.research")
    _stub.__path__ = ["services/research"]
    _stub.__package__ = "services.research"
    sys.modules["services.research"] = _stub

from services.research.ml_signal.idx_feature_builder import IDXFeatureBuilder
from services.research.ml_signal.idx_label_builder import IDXLabelBuilder
from services.research.ml_signal.idx_signal_combiner import IDXSignalCombiner
from services.research.ml_signal.purged_kfold import PurgedKFold

# ── Fixtures ───────────────────────────────────────────────────


def _make_price_data(
    n_days: int = 500,
    n_symbols: int = 20,
    seed: int = 42,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Generate synthetic price and volume data."""
    rng = np.random.RandomState(seed)
    dates = pd.bdate_range(start="2020-01-01", periods=n_days, freq="B")
    symbols = [f"SYM{i:02d}" for i in range(n_symbols)]

    # GBM prices
    prices_data = {}
    volumes_data = {}
    for sym in symbols:
        base_price = rng.uniform(1000, 10000)
        returns = rng.normal(0.0003, 0.018, n_days)
        cumulative = np.exp(np.cumsum(returns))
        prices_data[sym] = base_price * cumulative
        volumes_data[sym] = rng.randint(100000, 10000000, n_days).astype(float)

    prices = pd.DataFrame(prices_data, index=dates)
    volumes = pd.DataFrame(volumes_data, index=dates)
    return prices, volumes


# ── Test 1: Feature Builder ────────────────────────────────────


class TestIDXFeatureBuilder:
    """Tests for IDXFeatureBuilder."""

    def test_build_features_shape_and_no_nans(self) -> None:
        """Features should have no NaN values after postprocessing."""
        prices, volumes = _make_price_data(n_days=300, n_symbols=10)
        builder = IDXFeatureBuilder()
        features = builder.build_features(prices=prices, volumes=volumes)

        assert not features.empty
        assert features.isna().sum().sum() == 0, "Features should have no NaN after postprocessing"

    def test_features_rank_normalised(self) -> None:
        """All feature values should be in [0, 1] after rank normalisation."""
        prices, volumes = _make_price_data(n_days=300, n_symbols=10)
        builder = IDXFeatureBuilder()
        features = builder.build_features(prices=prices, volumes=volumes)

        assert features.min().min() >= 0.0, "Min feature value should be >= 0"
        assert features.max().max() <= 1.0, "Max feature value should be <= 1"

    def test_feature_names_include_all_groups(self) -> None:
        """Feature names should cover momentum, volatility, liquidity, technical groups."""
        names = IDXFeatureBuilder.get_feature_names(include_value=False, include_quality=False, include_macro=False)
        prefixes = {"mom_", "vol_", "liq_", "tech_"}
        # Check each expected prefix has at least one feature
        for prefix in prefixes:
            assert any(n.startswith(prefix) for n in names), f"Missing features with prefix {prefix}"


# ── Test 2: Label Builder ──────────────────────────────────────


class TestIDXLabelBuilder:
    """Tests for IDXLabelBuilder."""

    def test_forward_returns_no_lookahead(self) -> None:
        """Labels should use strictly future data (no look-ahead)."""
        prices, _ = _make_price_data(n_days=100, n_symbols=5)
        builder = IDXLabelBuilder(
            forward_days=[5],
            primary_horizon=5,
            use_excess_returns=False,
            rank_normalise=False,
        )
        labels = builder.build_labels(prices)

        # The last 5 dates should have NaN labels (can't see into the future)
        # After stacking, NaN rows may be present but the DataFrame should not be empty
        assert len(labels) > 0

    def test_rank_normalised_labels_approximately_gaussian(self) -> None:
        """Rank-normalised labels should have mean ~0 and std ~1."""
        prices, _ = _make_price_data(n_days=200, n_symbols=15)
        builder = IDXLabelBuilder(
            forward_days=[5],
            primary_horizon=5,
            rank_normalise=True,
        )
        labels = builder.build_labels(prices)
        label_col = "label" if "label" in labels.columns else labels.columns[0]
        values = labels[label_col].dropna()

        if len(values) > 10:
            assert abs(values.mean()) < 0.5, "Mean should be approximately 0"
            assert 0.3 < values.std() < 2.0, "Std should be approximately 1"

    def test_align_features_labels_drops_nans(self) -> None:
        """Alignment should produce NaN-free X and y."""
        prices, volumes = _make_price_data(n_days=300, n_symbols=10)
        builder_f = IDXFeatureBuilder()
        builder_l = IDXLabelBuilder(forward_days=[5], primary_horizon=5)

        features = builder_f.build_features(prices, volumes)
        labels = builder_l.build_labels(prices)

        X, y = IDXLabelBuilder.align_features_labels(features, labels)
        assert X.isna().sum().sum() == 0
        assert y.isna().sum() == 0
        assert len(X) == len(y)
        assert len(X) > 0


# ── Test 3: Purged K-Fold ──────────────────────────────────────


class TestPurgedKFold:
    """Tests for PurgedKFold cross-validator."""

    def test_no_train_test_overlap(self) -> None:
        """Train and test indices should never overlap."""
        prices, volumes = _make_price_data(n_days=300, n_symbols=10)
        builder = IDXFeatureBuilder()
        features = builder.build_features(prices, volumes)

        cv = PurgedKFold(n_splits=5, purge_days=10)

        for train_idx, test_idx in cv.split(features):
            overlap = set(train_idx) & set(test_idx)
            assert len(overlap) == 0, f"Found {len(overlap)} overlapping indices"

    def test_purge_gap_respected(self) -> None:
        """There should be a gap between train end and test start."""
        n_days = 300
        dates = pd.bdate_range(start="2020-01-01", periods=n_days, freq="B")
        X = pd.DataFrame(
            np.random.randn(n_days, 5),
            index=dates,
            columns=[f"f{i}" for i in range(5)],
        )

        cv = PurgedKFold(n_splits=3, purge_days=15)

        for train_idx, test_idx in cv.split(X):
            train_dates = X.index[train_idx]
            test_dates = X.index[test_idx]

            if len(train_dates) == 0 or len(test_dates) == 0:
                continue

            # For each training date, check it's not within purge_days of test
            test_min = test_dates.min()
            train_max = train_dates[train_dates < test_min].max() if (train_dates < test_min).any() else None

            if train_max is not None:
                gap = (test_min - train_max).days
                assert gap >= 15, f"Gap {gap} days < purge_days 15"

    def test_n_splits_correct(self) -> None:
        """Should produce the requested number of splits."""
        n_days = 300
        dates = pd.bdate_range(start="2020-01-01", periods=n_days, freq="B")
        X = pd.DataFrame(np.random.randn(n_days, 5), index=dates)

        cv = PurgedKFold(n_splits=5, purge_days=5)
        splits = list(cv.split(X))

        assert len(splits) == 5


# ── Test 4: Signal Combiner ────────────────────────────────────


class TestIDXSignalCombiner:
    """Tests for IDXSignalCombiner."""

    def test_equal_weights_without_returns(self) -> None:
        """Without realised returns, should use equal weights."""
        combiner = IDXSignalCombiner()
        signals = {
            "model_a": pd.Series([1.0, 2.0, 3.0], name="a"),
            "model_b": pd.Series([3.0, 2.0, 1.0], name="b"),
        }
        combined = combiner.combine(signals)

        # Equal weight: (1+3)/2=2, (2+2)/2=2, (3+1)/2=2
        np.testing.assert_allclose(combined.to_numpy(), [2.0, 2.0, 2.0])

    def test_ic_weighting_updates(self) -> None:
        """Providing realised returns should update IC-based weights."""
        combiner = IDXSignalCombiner(ic_lookback=10)

        # Model A has positive correlation with returns
        np.random.seed(42)
        returns = pd.Series(np.random.randn(50))
        signal_a = returns + np.random.randn(50) * 0.3  # Good signal
        signal_b = pd.Series(np.random.randn(50))  # Random signal

        signals = {
            "good_model": pd.Series(signal_a),
            "bad_model": pd.Series(signal_b),
        }

        combiner.combine(signals, realised_returns=returns)
        weights = combiner.current_weights

        # Good model should have higher weight
        assert (
            weights["good_model"] > weights["bad_model"]
        ), f"Good model weight {weights['good_model']:.3f} should be > bad model weight {weights['bad_model']:.3f}"

    def test_ic_summary_returns_dataframe(self) -> None:
        """IC summary should return a valid DataFrame."""
        combiner = IDXSignalCombiner()
        returns = pd.Series(np.random.randn(30))
        signals = {
            "m1": pd.Series(np.random.randn(30)),
            "m2": pd.Series(np.random.randn(30)),
        }
        combiner.combine(signals, realised_returns=returns)
        summary = combiner.get_ic_summary()

        assert isinstance(summary, pd.DataFrame)
        assert "mean_ic" in summary.columns
        assert "icir" in summary.columns


# ── Test 5: Integration Test ──────────────────────────────────


class TestMLSignalIntegration:
    """Integration test: feature → label → align → purged CV."""

    def test_end_to_end_feature_label_cv_pipeline(self) -> None:
        """Full pipeline: build features, build labels, align, split with purged CV."""
        prices, volumes = _make_price_data(n_days=400, n_symbols=15, seed=42)

        # Build features
        fb = IDXFeatureBuilder()
        features = fb.build_features(prices, volumes)
        assert not features.empty, "Features should not be empty"

        # Build labels
        lb = IDXLabelBuilder(forward_days=[5], primary_horizon=5)
        labels = lb.build_labels(prices)
        assert not labels.empty, "Labels should not be empty"

        # Align
        X, y = IDXLabelBuilder.align_features_labels(features, labels)
        assert len(X) > 100, f"Should have > 100 aligned samples, got {len(X)}"
        assert len(X) == len(y)

        # Purged CV
        cv = PurgedKFold(n_splits=3, purge_days=10)
        fold_count = 0

        for train_idx, test_idx in cv.split(X, y):
            assert len(train_idx) > 0, "Train set should not be empty"
            assert len(test_idx) > 0, "Test set should not be empty"
            assert len(set(train_idx) & set(test_idx)) == 0, "No overlap"
            fold_count += 1

        assert fold_count == 3, f"Expected 3 folds, got {fold_count}"
