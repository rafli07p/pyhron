"""Factor engine for the Pyhron trading platform.

Computes cross-sectional alpha factors (momentum, mean-reversion,
volatility, value) with vectorised numpy/pandas calculations and
produces factor analysis reports.
"""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Any

import numpy as np
import pandas as pd
import structlog
from scipy import stats

from shared.schemas.research_events import FactorCategory, FactorResult, Frequency

logger = structlog.get_logger(__name__)


class FactorEngine:
    """Cross-sectional factor scoring and analysis engine.

    All factor calculations are fully vectorised with numpy/pandas.
    Factor scores are cross-sectionally ranked and normalised to
    Z-scores for comparability.

    Parameters
    ----------
    risk_free_rate:
        Annualised risk-free rate for Sharpe calculations.
    """

    def __init__(self, risk_free_rate: float = 0.05) -> None:
        self._rf = risk_free_rate
        self._log = logger.bind(component="FactorEngine")

    # -- Helper: cross-sectional Z-score ------------------------------------

    @staticmethod
    def _zscore(df: pd.DataFrame) -> pd.DataFrame:
        """Cross-sectional Z-score normalisation (row-wise)."""
        return df.sub(df.mean(axis=1), axis=0).div(df.std(axis=1), axis=0).fillna(0)

    # -- Factor calculations -------------------------------------------------

    def calculate_momentum(
        self,
        prices: pd.DataFrame,
        lookback: int = 252,
        skip_recent: int = 21,
        tenant_id: str = "default",
    ) -> pd.DataFrame:
        """Calculate cross-sectional momentum factor.

        Momentum = cumulative return over [t-lookback, t-skip_recent],
        skipping the most recent *skip_recent* days to avoid short-term
        reversal effects.

        Parameters
        ----------
        prices:
            DataFrame of close prices (index=dates, columns=symbols).
        lookback:
            Total lookback window in trading days.
        skip_recent:
            Number of recent days to exclude.

        Returns
        -------
        pd.DataFrame
            Cross-sectional Z-scored momentum factors.
        """
        self._log.info("calculate_momentum", lookback=lookback, skip_recent=skip_recent, tenant_id=tenant_id)
        lagged = prices.shift(skip_recent)
        momentum_raw = lagged.pct_change(lookback - skip_recent)
        return self._zscore(momentum_raw)

    def calculate_mean_reversion(
        self,
        prices: pd.DataFrame,
        lookback: int = 21,
        tenant_id: str = "default",
    ) -> pd.DataFrame:
        """Calculate short-term mean-reversion factor.

        Factor = negative of the Z-score of recent returns, so
        recently underperforming stocks get a positive score.

        Parameters
        ----------
        prices:
            Close prices DataFrame.
        lookback:
            Short-term lookback window in trading days.
        """
        self._log.info("calculate_mean_reversion", lookback=lookback, tenant_id=tenant_id)
        recent_returns = prices.pct_change(lookback)
        # Invert: losers get high scores
        return -self._zscore(recent_returns)

    def calculate_volatility(
        self,
        prices: pd.DataFrame,
        lookback: int = 63,
        tenant_id: str = "default",
    ) -> pd.DataFrame:
        """Calculate realised-volatility factor (low vol = high score).

        Parameters
        ----------
        prices:
            Close prices DataFrame.
        lookback:
            Window for volatility estimation (trading days).

        Returns
        -------
        pd.DataFrame
            Z-scored factor where low-volatility names score highest.
        """
        self._log.info("calculate_volatility", lookback=lookback, tenant_id=tenant_id)
        daily_returns = prices.pct_change()
        vol = daily_returns.rolling(window=lookback).std() * np.sqrt(252)
        # Invert: lower vol = higher score
        return -self._zscore(vol)

    def calculate_value_factor(
        self,
        fundamental_data: pd.DataFrame,
        metric: str = "earnings_yield",
        tenant_id: str = "default",
    ) -> pd.DataFrame:
        """Calculate a value factor from fundamental data.

        Parameters
        ----------
        fundamental_data:
            DataFrame with index=dates, columns=symbols, values=the
            chosen value metric (e.g. earnings yield, book-to-price).
        metric:
            Name of the fundamental metric (for logging).

        Returns
        -------
        pd.DataFrame
            Cross-sectional Z-scored value factor.
        """
        self._log.info("calculate_value_factor", metric=metric, tenant_id=tenant_id)
        return self._zscore(fundamental_data)

    # -- Full factor analysis ------------------------------------------------

    def run_factor_analysis(
        self,
        factor_scores: pd.DataFrame,
        forward_returns: pd.DataFrame,
        factor_name: str,
        factor_category: FactorCategory = FactorCategory.CUSTOM,
        tenant_id: str = "default",
        num_quintiles: int = 5,
    ) -> FactorResult:
        """Run a full cross-sectional factor analysis.

        Computes information coefficient, quintile spreads, and
        risk-adjusted factor return statistics.

        Parameters
        ----------
        factor_scores:
            DataFrame of factor Z-scores (index=dates, columns=symbols).
        forward_returns:
            Corresponding forward returns for the same dates/symbols.
        factor_name:
            Human-readable name for the factor.
        factor_category:
            Category enum for the result schema.
        num_quintiles:
            Number of quantile buckets for spread analysis.

        Returns
        -------
        FactorResult
            Schema-compliant result with all metrics populated.
        """
        self._log.info(
            "run_factor_analysis",
            factor=factor_name,
            category=factor_category,
            tenant_id=tenant_id,
        )

        # Align data
        common_idx = factor_scores.index.intersection(forward_returns.index)
        common_cols = factor_scores.columns.intersection(forward_returns.columns)
        scores = factor_scores.loc[common_idx, common_cols]
        fwd = forward_returns.loc[common_idx, common_cols]

        # 1. Information coefficient (rank correlation per period)
        ic_series: list[float] = []
        for dt in common_idx:
            s = scores.loc[dt].dropna()
            r = fwd.loc[dt].dropna()
            common = s.index.intersection(r.index)
            if len(common) < 5:
                continue
            corr, _ = stats.spearmanr(s[common], r[common])
            if not np.isnan(corr):
                ic_series.append(float(corr))

        ic_arr = np.array(ic_series)
        ic_mean = float(np.mean(ic_arr)) if len(ic_arr) > 0 else 0.0
        ic_std = float(np.std(ic_arr, ddof=1)) if len(ic_arr) > 1 else 1.0
        ic_ir = ic_mean / ic_std if ic_std > 0 else 0.0

        # 2. Quintile returns
        quintile_returns: list[float] = []
        long_short_returns: list[float] = []

        for dt in common_idx:
            s = scores.loc[dt].dropna()
            r = fwd.loc[dt].dropna()
            common = s.index.intersection(r.index)
            if len(common) < num_quintiles:
                continue

            ranked = s[common].rank(method="first")
            quantile_labels = pd.qcut(ranked, num_quintiles, labels=False, duplicates="drop")

            q_rets = []
            for q in range(num_quintiles):
                mask = quantile_labels == q
                if mask.sum() > 0:
                    q_rets.append(float(r[common][mask].mean()))
                else:
                    q_rets.append(0.0)

            if len(q_rets) == num_quintiles:
                for i, qr in enumerate(q_rets):
                    if len(quintile_returns) <= i:
                        quintile_returns.append(0.0)
                    # Running average
                    n = len(long_short_returns) + 1
                    quintile_returns[i] = (
                        quintile_returns[i] * (n - 1) + qr
                    ) / n

                ls = q_rets[-1] - q_rets[0]  # top quintile - bottom
                long_short_returns.append(ls)

        # 3. Factor return series (long-short)
        ls_arr = np.array(long_short_returns)
        cum_return = float(np.sum(ls_arr)) if len(ls_arr) > 0 else 0.0

        # Annualised return
        n_periods = len(ls_arr)
        if n_periods > 0:
            avg_daily = np.mean(ls_arr)
            ann_return = float(avg_daily * 252)
        else:
            ann_return = 0.0

        # Sharpe
        if len(ls_arr) > 1:
            sharpe = float(np.mean(ls_arr) / np.std(ls_arr, ddof=1) * np.sqrt(252))
        else:
            sharpe = 0.0

        # Max drawdown of long-short
        if len(ls_arr) > 0:
            cum_curve = np.cumsum(ls_arr)
            running_max = np.maximum.accumulate(cum_curve)
            dd = cum_curve - running_max
            mdd = float(np.min(dd))
        else:
            mdd = 0.0

        # T-statistic and p-value
        if len(ls_arr) > 1:
            t_stat, p_val = stats.ttest_1samp(ls_arr, 0)
        else:
            t_stat, p_val = 0.0, 1.0

        # Turnover (simplified: avg absolute change in factor rank per period)
        rank_changes = scores.rank(axis=1).diff().abs()
        avg_turnover = float(rank_changes.mean().mean()) / max(len(common_cols), 1)

        # Determine actual date range
        start = common_idx.min()
        end = common_idx.max()
        start_d = start.date() if hasattr(start, "date") else date.today()
        end_d = end.date() if hasattr(end, "date") else date.today()
        # Ensure start < end for schema validation
        if start_d >= end_d:
            end_d = start_d + pd.Timedelta(days=1)
            end_d = end_d.date() if hasattr(end_d, "date") else end_d

        return FactorResult(
            tenant_id=tenant_id,
            factor_name=factor_name,
            factor_category=factor_category,
            start_date=start_d,
            end_date=end_d,
            symbols=list(common_cols),
            frequency=Frequency.DAILY,
            returns=ls_arr.tolist() if len(ls_arr) > 0 else [],
            cumulative_return=Decimal(str(round(cum_return, 6))),
            annualized_return=Decimal(str(round(ann_return, 6))),
            sharpe_ratio=Decimal(str(round(sharpe, 4))),
            max_drawdown=Decimal(str(round(min(mdd, 0.0), 6))),
            t_statistic=Decimal(str(round(float(t_stat), 4))),
            p_value=Decimal(str(round(max(0.0, min(1.0, float(p_val))), 6))),
            ic_mean=Decimal(str(round(ic_mean, 6))),
            ic_ir=Decimal(str(round(ic_ir, 4))),
            turnover=Decimal(str(round(min(max(avg_turnover, 0.0), 1.0), 4))),
            long_short_return=Decimal(str(round(cum_return, 6))),
            quintile_returns=[round(q, 6) for q in quintile_returns],
        )


__all__ = [
    "FactorEngine",
]
