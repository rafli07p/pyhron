"""Hierarchical Risk Parity (Lopez de Prado 2016).

Allocates portfolio weights using hierarchical clustering and
recursive bisection — no optimisation required, robust to
estimation error in the covariance matrix.
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

import numpy as np
from scipy.cluster.hierarchy import leaves_list, linkage
from scipy.spatial.distance import squareform

if TYPE_CHECKING:
    import pandas as pd


class HRPOptimizer:
    """Hierarchical Risk Parity optimizer.

    Parameters
    ----------
    linkage_method:
        Hierarchical clustering linkage method (default ``"single"``).
    """

    def __init__(self, linkage_method: str = "single") -> None:
        self._linkage_method = linkage_method
        self._linkage_matrix: np.ndarray | None = None

    def optimize(
        self,
        returns: pd.DataFrame,
        cov: np.ndarray | None = None,
    ) -> dict[str, float]:
        """Compute HRP weights.

        Parameters
        ----------
        returns:
            (T × N) daily returns with asset names as columns.
        cov:
            Optional pre-computed covariance matrix.  If ``None``,
            uses Ledoit-Wolf via ``pyhron.portfolio.covariance``.

        Returns
        -------
        dict[str, float]
            Asset weights summing to 1.0.
        """
        symbols = list(returns.columns)
        n = len(symbols)

        if cov is None:
            from pyhron.portfolio.covariance import LedoitWolfIDX

            cov = LedoitWolfIDX().fit(returns)

        # Step 1: Correlation matrix
        std = np.sqrt(np.diag(cov))
        std_safe = np.where(std > 0, std, 1e-10)
        corr = cov / np.outer(std_safe, std_safe)
        corr = np.clip(corr, -1, 1)

        # Step 2: Distance matrix
        dist = np.sqrt(0.5 * (1 - corr))
        np.fill_diagonal(dist, 0)

        # Step 3: Hierarchical clustering
        condensed = squareform(dist, checks=False)
        self._linkage_matrix = linkage(condensed, method=self._linkage_method)

        # Step 4: Quasi-diagonalise
        sort_ix = list(leaves_list(self._linkage_matrix).astype(int))
        sorted_cov = cov[np.ix_(sort_ix, sort_ix)]

        # Step 5: Recursive bisection
        weights = np.ones(n)
        cluster_items: list[list[int]] = [list(range(n))]

        while cluster_items:
            new_clusters: list[list[int]] = []
            for cluster in cluster_items:
                if len(cluster) <= 1:
                    continue
                mid = len(cluster) // 2
                left = cluster[:mid]
                right = cluster[mid:]

                # IVP for each sub-cluster
                ivp_left = self._inverse_variance_portfolio(sorted_cov, left)
                ivp_right = self._inverse_variance_portfolio(sorted_cov, right)

                alpha = ivp_left / (ivp_left + ivp_right) if (ivp_left + ivp_right) > 0 else 0.5

                for i in left:
                    weights[i] *= alpha
                for i in right:
                    weights[i] *= 1 - alpha

                if len(left) > 1:
                    new_clusters.append(left)
                if len(right) > 1:
                    new_clusters.append(right)

            cluster_items = new_clusters

        # Map back to original order
        total = weights.sum()
        if total > 0:
            weights = weights / total

        result = {}
        for i, orig_idx in enumerate(sort_ix):
            result[symbols[orig_idx]] = float(weights[i])

        return result

    @staticmethod
    def _inverse_variance_portfolio(cov: np.ndarray, indices: list[int]) -> float:
        """Compute inverse-variance portfolio weight for a cluster.

        Returns the reciprocal of the cluster's portfolio variance
        using equal weights within the cluster.
        """
        sub_cov = cov[np.ix_(indices, indices)]
        n = len(indices)
        w = np.ones(n) / n
        var = w @ sub_cov @ w
        return 1.0 / var if var > 0 else 1e10

    def plot_dendrogram(self, save_path: Path, symbols: list[str] | None = None) -> None:
        """Plot and save the dendrogram.

        Parameters
        ----------
        save_path:
            File path to save the figure.
        symbols:
            Optional asset labels.
        """
        if self._linkage_matrix is None:
            msg = "Call optimize() first"
            raise RuntimeError(msg)

        import matplotlib

        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        from scipy.cluster.hierarchy import dendrogram

        fig, ax = plt.subplots(figsize=(12, 6))
        dendrogram(
            self._linkage_matrix,
            labels=symbols,
            ax=ax,
            leaf_rotation=90,
        )
        ax.set_title("HRP Dendrogram")
        ax.set_ylabel("Distance")
        fig.tight_layout()
        fig.savefig(save_path, dpi=150)
        plt.close(fig)
