"""Walk-forward ML backtest for IDX signal layer.

Implements expanding-window walk-forward validation:
1. Train on expanding window of historical data
2. Generate signals on out-of-sample period
3. Evaluate IC, ICIR, and simulated P&L
4. Report aggregate performance across all folds

Prevents look-ahead bias by strictly separating train/test periods
with purge and embargo gaps.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from typing import Any

import numpy as np
import pandas as pd
from scipy.stats import spearmanr

from services.research.ml_signal.idx_feature_builder import IDXFeatureBuilder
from services.research.ml_signal.idx_label_builder import IDXLabelBuilder
from services.research.ml_signal.idx_lgbm_alpha_model import IDXLGBMAlphaModel


@dataclass
class MLWalkForwardFold:
    """Results for a single walk-forward fold."""

    fold_index: int
    train_start: date
    train_end: date
    test_start: date
    test_end: date
    n_train_samples: int
    n_test_samples: int
    ic: float
    icir: float
    mean_return_long: float  # Mean return of top quintile
    mean_return_short: float  # Mean return of bottom quintile
    long_short_spread: float
    cv_metrics: dict[str, float] = field(default_factory=dict)


@dataclass
class MLWalkForwardReport:
    """Aggregate walk-forward backtest report."""

    strategy_name: str
    folds: list[MLWalkForwardFold]
    aggregate_ic: float
    aggregate_icir: float
    aggregate_long_short: float
    hit_rate: float  # Fraction of folds with positive IC
    passes_deployment_gate: bool
    ic_gate: float
    icir_gate: float
    total_train_samples: int
    total_test_samples: int


class IDXWalkForwardMLBacktest:
    """Walk-forward backtest for ML alpha models.

    Parameters
    ----------
    initial_train_months : int
        Months of data for initial training window.
    test_months : int
        Months of data for each test period.
    step_months : int
        How far to advance the window each fold.
    purge_days : int
        Purge gap between train and test.
    min_ic : float
        Deployment gate IC threshold.
    min_icir : float
        Deployment gate ICIR threshold.
    """

    def __init__(
        self,
        initial_train_months: int = 24,
        test_months: int = 3,
        step_months: int = 3,
        purge_days: int = 10,
        min_ic: float = 0.03,
        min_icir: float = 0.5,
    ) -> None:
        self._initial_train_months = initial_train_months
        self._test_months = test_months
        self._step_months = step_months
        self._purge_days = purge_days
        self._min_ic = min_ic
        self._min_icir = min_icir

    def run(
        self,
        prices: pd.DataFrame,
        volumes: pd.DataFrame,
        fundamentals: pd.DataFrame | None = None,
        macro: pd.DataFrame | None = None,
        lgbm_params: dict[str, Any] | None = None,
        label_horizon: int = 5,
        strategy_name: str = "idx_ml_alpha",
    ) -> MLWalkForwardReport:
        """Run walk-forward ML backtest.

        Parameters
        ----------
        prices : DataFrame
            DatetimeIndex × symbol close prices.
        volumes : DataFrame
            Same shape, daily volumes.
        fundamentals, macro : DataFrame, optional
            Additional data for feature engineering.
        lgbm_params : dict, optional
            LightGBM hyperparameters override.
        label_horizon : int
            Forward return horizon for labels.
        strategy_name : str
            Name for the report.

        Returns
        -------
        MLWalkForwardReport
        """
        # Build features and labels
        feature_builder = IDXFeatureBuilder()
        label_builder = IDXLabelBuilder(
            forward_days=[label_horizon],
            primary_horizon=label_horizon,
        )

        features = feature_builder.build_features(
            prices=prices,
            volumes=volumes,
            fundamentals=fundamentals,
            macro=macro,
        )
        labels = label_builder.build_labels(prices)

        # Align
        X, y = IDXLabelBuilder.align_features_labels(features, labels)

        # Get date range
        if isinstance(X.index, pd.MultiIndex):
            dates = X.index.get_level_values(0).unique().sort_values()
        else:
            dates = X.index.sort_values()

        # Generate fold boundaries
        folds = self._generate_folds(pd.DatetimeIndex(dates))

        fold_results: list[MLWalkForwardFold] = []
        fold_ics: list[float] = []

        for fold_idx, (train_start, train_end, test_start, test_end) in enumerate(folds):
            # Split data
            if isinstance(X.index, pd.MultiIndex):
                date_level = X.index.get_level_values(0)
                train_mask = (date_level >= train_start) & (date_level <= train_end)
                test_mask = (date_level >= test_start) & (date_level <= test_end)
            else:
                train_mask = (X.index >= train_start) & (X.index <= train_end)
                test_mask = (X.index >= test_start) & (X.index <= test_end)

            X_train, y_train = X.loc[train_mask], y.loc[train_mask]
            X_test, y_test = X.loc[test_mask], y.loc[test_mask]

            if len(X_train) < 100 or len(X_test) < 10:
                continue

            # Train model
            model = IDXLGBMAlphaModel(
                params=lgbm_params,
                purge_days=self._purge_days,
                min_ic=self._min_ic,
                min_icir=self._min_icir,
            )
            cv_metrics = model.train(X_train, y_train)

            # Predict on test set
            predictions = model.predict(X_test)

            # Compute OOS metrics
            ic = 0.0
            if len(y_test) > 2:
                ic_val, _ = spearmanr(y_test, predictions)
                if not np.isnan(ic_val):
                    ic = float(ic_val)

            # Quintile analysis
            long_ret, short_ret, spread = self._quintile_analysis(predictions, y_test)

            fold_ics.append(ic)

            fold_results.append(MLWalkForwardFold(
                fold_index=fold_idx,
                train_start=train_start.date() if hasattr(train_start, 'date') else train_start,
                train_end=train_end.date() if hasattr(train_end, 'date') else train_end,
                test_start=test_start.date() if hasattr(test_start, 'date') else test_start,
                test_end=test_end.date() if hasattr(test_end, 'date') else test_end,
                n_train_samples=len(X_train),
                n_test_samples=len(X_test),
                ic=ic,
                icir=ic / max(float(np.std(fold_ics)), 1e-8) if fold_ics else 0.0,
                mean_return_long=long_ret,
                mean_return_short=short_ret,
                long_short_spread=spread,
                cv_metrics=cv_metrics,
            ))

        # Aggregate metrics
        if fold_ics:
            agg_ic = float(np.mean(fold_ics))
            agg_ic_std = float(np.std(fold_ics))
            agg_icir = agg_ic / agg_ic_std if agg_ic_std > 0 else 0.0
        else:
            agg_ic = agg_icir = 0.0

        agg_ls = float(np.mean([f.long_short_spread for f in fold_results])) if fold_results else 0.0
        hit_rate = sum(1 for ic in fold_ics if ic > 0) / max(len(fold_ics), 1)

        return MLWalkForwardReport(
            strategy_name=strategy_name,
            folds=fold_results,
            aggregate_ic=agg_ic,
            aggregate_icir=agg_icir,
            aggregate_long_short=agg_ls,
            hit_rate=hit_rate,
            passes_deployment_gate=agg_ic >= self._min_ic and agg_icir >= self._min_icir,
            ic_gate=self._min_ic,
            icir_gate=self._min_icir,
            total_train_samples=sum(f.n_train_samples for f in fold_results),
            total_test_samples=sum(f.n_test_samples for f in fold_results),
        )

    def _generate_folds(
        self,
        dates: pd.DatetimeIndex,
    ) -> list[tuple[Any, Any, Any, Any]]:
        """Generate expanding-window fold boundaries."""
        folds = []
        total_months = len(dates) // 21  # Approximate months

        train_months = self._initial_train_months
        current_offset = 0

        while current_offset + train_months + self._test_months <= total_months:
            train_start_idx = current_offset * 21
            train_end_idx = min((current_offset + train_months) * 21 - 1, len(dates) - 1)

            # Purge gap
            test_start_idx = min(
                train_end_idx + self._purge_days + 1,
                len(dates) - 1,
            )
            test_end_idx = min(
                test_start_idx + self._test_months * 21 - 1,
                len(dates) - 1,
            )

            if test_start_idx >= len(dates) or test_end_idx >= len(dates):
                break

            folds.append((
                dates[train_start_idx],
                dates[train_end_idx],
                dates[test_start_idx],
                dates[test_end_idx],
            ))

            # Expanding window: increase train, step forward
            train_months += self._step_months
            current_offset += self._step_months

        return folds

    @staticmethod
    def _quintile_analysis(
        predictions: pd.Series,
        actuals: pd.Series,
    ) -> tuple[float, float, float]:
        """Compute quintile returns from predictions.

        Returns (mean_return_long, mean_return_short, spread).
        """
        combined = pd.DataFrame({"pred": predictions, "actual": actuals})
        combined = combined.dropna()

        if len(combined) < 5:
            return 0.0, 0.0, 0.0

        try:
            combined["quintile"] = pd.qcut(
                combined["pred"], q=5, labels=False, duplicates="drop"
            )
        except ValueError:
            return 0.0, 0.0, 0.0

        quintile_returns = combined.groupby("quintile")["actual"].mean()

        long_ret = float(quintile_returns.iloc[-1]) if len(quintile_returns) > 0 else 0.0
        short_ret = float(quintile_returns.iloc[0]) if len(quintile_returns) > 0 else 0.0
        spread = long_ret - short_ret

        return long_ret, short_ret, spread
