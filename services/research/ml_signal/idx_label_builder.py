"""Label construction for IDX ML signal layer.

Constructs forward return labels with:
- Configurable forward horizons (default 5d, 10d, 21d)
- Excess returns over equal-weighted market
- Rank-normalised to [0, 1] cross-sectionally (Gaussian quantile transform)
- No look-ahead bias: labels use strictly future data relative to feature date
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from scipy.stats import norm


class IDXLabelBuilder:
    """Constructs cross-sectional labels for supervised learning.

    Parameters
    ----------
    forward_days : list[int]
        Forward return horizons in trading days.
    primary_horizon : int
        The horizon used as the primary training label.
    use_excess_returns : bool
        If True, subtract cross-sectional mean (market return) from raw returns.
    rank_normalise : bool
        If True, apply rank + inverse-normal transform to produce Gaussian labels.
    """

    def __init__(
        self,
        forward_days: list[int] | None = None,
        primary_horizon: int = 5,
        use_excess_returns: bool = True,
        rank_normalise: bool = True,
    ) -> None:
        self._forward_days = forward_days or [5, 10, 21]
        self._primary_horizon = primary_horizon
        self._use_excess_returns = use_excess_returns
        self._rank_normalise = rank_normalise

        if primary_horizon not in self._forward_days:
            self._forward_days.append(primary_horizon)

    def build_labels(self, prices: pd.DataFrame) -> pd.DataFrame:
        """Build forward return labels.

        Parameters
        ----------
        prices : DataFrame
            DatetimeIndex rows × symbol columns, close prices.

        Returns
        -------
        DataFrame
            MultiIndex (date, symbol) rows × label columns.
            Columns: fwd_ret_{n}d for each horizon, plus 'label' for primary.
        """
        all_labels = {}

        for horizon in self._forward_days:
            # Forward return: price at t+h / price at t - 1
            fwd_ret = prices.shift(-horizon) / prices - 1
            col_name = f"fwd_ret_{horizon}d"

            if self._use_excess_returns:
                # Subtract cross-sectional mean (equal-weighted market return)
                market_ret = fwd_ret.mean(axis=1)
                fwd_ret = fwd_ret.sub(market_ret, axis=0)

            if self._rank_normalise:
                fwd_ret = self._rank_normalise_cs(fwd_ret)

            all_labels[col_name] = fwd_ret

        # Stack to MultiIndex
        combined = pd.concat(all_labels, axis=1)

        # Stack: (date, symbol) index
        result = combined.stack(future_stack=True)
        if isinstance(result, pd.Series):
            result = result.to_frame()

        # Set primary label
        primary_col = f"fwd_ret_{self._primary_horizon}d"
        if primary_col in result.columns:
            result["label"] = result[primary_col]
        elif isinstance(result.columns, pd.MultiIndex):
            # Handle nested column structure
            result = result.droplevel(0, axis=1) if result.columns.nlevels > 1 else result

        return result

    def _rank_normalise_cs(self, df: pd.DataFrame) -> pd.DataFrame:
        """Cross-sectional rank normalisation with inverse-normal transform.

        For each date, ranks securities and maps to N(0,1) quantiles.
        This produces approximately Gaussian-distributed labels
        while preserving the cross-sectional ordering.
        """
        result = df.copy()

        for idx in df.index:
            row = df.loc[idx]
            valid = row.dropna()
            if len(valid) < 3:
                continue
            # Rank to (0, 1) range, avoiding 0 and 1 for inverse normal
            n = len(valid)
            ranks = valid.rank()
            # Use (rank - 0.5) / n to map to (0, 1) open interval
            uniform = (ranks - 0.5) / n
            # Inverse normal CDF
            result.loc[idx, valid.index] = norm.ppf(uniform)

        return result

    def build_classification_labels(
        self,
        prices: pd.DataFrame,
        horizon: int = 5,
        n_classes: int = 3,
    ) -> pd.DataFrame:
        """Build classification labels (tercile bins).

        Parameters
        ----------
        prices : DataFrame
            Close prices.
        horizon : int
            Forward return horizon.
        n_classes : int
            Number of classes (3 = bottom/middle/top).

        Returns
        -------
        DataFrame
            MultiIndex (date, symbol) with 'label_class' column (0, 1, 2).
        """
        fwd_ret = prices.shift(-horizon) / prices - 1

        if self._use_excess_returns:
            market_ret = fwd_ret.mean(axis=1)
            fwd_ret = fwd_ret.sub(market_ret, axis=0)

        # Cross-sectional quantile binning
        labels = fwd_ret.copy()
        for idx in fwd_ret.index:
            row = fwd_ret.loc[idx].dropna()
            if len(row) < n_classes:
                continue
            bins = pd.qcut(row, q=n_classes, labels=False, duplicates="drop")
            labels.loc[idx, bins.index] = bins.values

        stacked = labels.stack(future_stack=True)
        if isinstance(stacked, pd.DataFrame):
            stacked.columns = pd.Index(["label_class"])
            return stacked
        return stacked.to_frame("label_class")

    @staticmethod
    def align_features_labels(
        features: pd.DataFrame,
        labels: pd.DataFrame,
    ) -> tuple[pd.DataFrame, pd.Series]:
        """Align feature matrix with labels, dropping NaN rows.

        Parameters
        ----------
        features : DataFrame
            MultiIndex (date, symbol) × feature columns.
        labels : DataFrame
            MultiIndex (date, symbol) with 'label' column.

        Returns
        -------
        tuple of (X, y)
            X: aligned feature DataFrame
            y: aligned label Series
        """
        # Get the label column
        if "label" in labels.columns:
            y = labels["label"]
        else:
            y = labels.iloc[:, 0]

        # Inner join on index
        common_idx = features.index.intersection(y.index)
        X = features.loc[common_idx]
        y = y.loc[common_idx]

        # Drop rows with any NaN
        mask = X.notna().all(axis=1) & y.notna()
        return X.loc[mask], y.loc[mask]
