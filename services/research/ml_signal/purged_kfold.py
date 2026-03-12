"""Purged K-Fold Cross-Validation (Lopez de Prado, 2018).

Prevents data leakage in time-series cross-validation by:
1. Purging: Removing training samples whose labels overlap with test period
2. Embargo: Adding a gap between training and test sets to prevent information leakage

Reference: Advances in Financial Machine Learning, Chapter 7.
"""

from __future__ import annotations

from typing import Iterator

import numpy as np
import pandas as pd


class PurgedKFold:
    """Purged K-Fold cross-validator for financial time series.

    Parameters
    ----------
    n_splits : int
        Number of folds (default 5).
    purge_days : int
        Number of days to purge from training set around test boundaries.
        Should be >= forward return horizon used for labels.
    embargo_pct : float
        Fraction of test set size to use as embargo gap after each
        test set boundary (default 0.01 = 1%).
    """

    def __init__(
        self,
        n_splits: int = 5,
        purge_days: int = 5,
        embargo_pct: float = 0.01,
    ) -> None:
        self._n_splits = n_splits
        self._purge_days = purge_days
        self._embargo_pct = embargo_pct

    @property
    def n_splits(self) -> int:
        return self._n_splits

    def split(
        self,
        X: pd.DataFrame,
        y: pd.Series | None = None,
        groups: pd.Series | None = None,
    ) -> Iterator[tuple[np.ndarray, np.ndarray]]:
        """Generate purged train/test splits.

        Parameters
        ----------
        X : DataFrame
            Feature matrix with DatetimeIndex or MultiIndex (date, symbol).
        y : Series, optional
            Labels (unused, for sklearn compatibility).
        groups : Series, optional
            Group labels (unused).

        Yields
        ------
        tuple of (train_indices, test_indices)
            Integer indices into X.
        """
        # Extract dates from index
        if isinstance(X.index, pd.MultiIndex):
            dates = X.index.get_level_values(0)
        else:
            dates = X.index

        unique_dates = np.sort(dates.unique())
        n_dates = len(unique_dates)

        if n_dates < self._n_splits:
            raise ValueError(
                f"Not enough unique dates ({n_dates}) for {self._n_splits} splits"
            )

        # Create date-based folds
        fold_size = n_dates // self._n_splits
        embargo_size = max(1, int(fold_size * self._embargo_pct))

        for fold_idx in range(self._n_splits):
            test_start = fold_idx * fold_size
            test_end = min((fold_idx + 1) * fold_size, n_dates)

            test_dates = unique_dates[test_start:test_end]
            test_date_min = test_dates[0]
            test_date_max = test_dates[-1]

            # Determine purge boundaries
            # Purge training samples that could leak into test
            purge_start = test_date_min - pd.Timedelta(days=self._purge_days)
            purge_end = test_date_max + pd.Timedelta(days=self._purge_days)

            # Embargo: additional gap after test period
            embargo_end = test_date_max + pd.Timedelta(days=self._purge_days + embargo_size)

            # Build train dates: all dates NOT in [purge_start, embargo_end]
            train_mask = (dates < purge_start) | (dates > embargo_end)
            test_mask = (dates >= test_date_min) & (dates <= test_date_max)

            train_indices = np.where(train_mask)[0]
            test_indices = np.where(test_mask)[0]

            if len(train_indices) == 0 or len(test_indices) == 0:
                continue

            yield train_indices, test_indices

    def get_n_splits(
        self,
        X: pd.DataFrame | None = None,
        y: pd.Series | None = None,
        groups: pd.Series | None = None,
    ) -> int:
        """Return number of splits."""
        return self._n_splits

    def compute_train_test_gap(
        self,
        X: pd.DataFrame,
    ) -> list[dict[str, object]]:
        """Compute and return metadata about each fold's train/test gap.

        Returns list of dicts with:
        - fold: int
        - train_size: int
        - test_size: int
        - purge_days: int
        - embargo_days: int
        - train_end_date: date
        - test_start_date: date
        - gap_days: int (actual calendar days between train end and test start)
        """
        metadata = []
        if isinstance(X.index, pd.MultiIndex):
            dates = X.index.get_level_values(0)
        else:
            dates = X.index

        for fold_idx, (train_idx, test_idx) in enumerate(self.split(X)):
            train_dates = dates[train_idx]
            test_dates = dates[test_idx]

            train_end = train_dates.max()
            test_start = test_dates.min()
            gap = (test_start - train_end).days if hasattr(test_start - train_end, "days") else 0

            metadata.append({
                "fold": fold_idx,
                "train_size": len(train_idx),
                "test_size": len(test_idx),
                "purge_days": self._purge_days,
                "embargo_days": max(1, int(len(test_idx) * self._embargo_pct)),
                "train_end_date": train_end,
                "test_start_date": test_start,
                "gap_days": gap,
            })

        return metadata
