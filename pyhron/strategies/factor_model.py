"""Fama-French 3-Factor Model adapted for IDX.

Constructs IDX-specific SMB and HML factors, estimates factor loadings
via OLS, and ranks stocks by Jensen's alpha.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


@dataclass
class FactorExposure:
    """Factor loading estimates for a single stock."""

    symbol: str
    alpha: float
    beta_mkt: float
    beta_smb: float
    beta_hml: float
    r_squared: float


class FactorModelStrategy:
    """Fama-French 3-Factor Model strategy for IDX.

    Long top-decile stocks by Jensen's alpha, weighted by HRP.
    Rebalances monthly.

    Parameters
    ----------
    estimation_window:
        OLS regression window in months (default 36).
    rebalance_frequency:
        Rebalance every N trading days (default 21).
    top_decile_pct:
        Fraction of universe to hold long (default 0.10).
    max_beta_mkt:
        Maximum market beta before alerting (default 1.5).
    name:
        Strategy name.
    """

    def __init__(
        self,
        estimation_window: int = 36,
        rebalance_frequency: int = 21,
        top_decile_pct: float = 0.10,
        max_beta_mkt: float = 1.5,
        name: str = "factor_model",
    ) -> None:
        self._window = estimation_window
        self._rebal_freq = rebalance_frequency
        self._top_pct = top_decile_pct
        self._max_beta = max_beta_mkt
        self._name = name

    @property
    def name(self) -> str:
        return self._name

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "estimation_window": self._window,
            "rebalance_frequency": self._rebal_freq,
            "top_decile_pct": self._top_pct,
            "max_beta_mkt": self._max_beta,
        }

    @staticmethod
    def construct_factors(
        returns: pd.DataFrame,
        market_caps: pd.DataFrame,
        book_to_market: pd.DataFrame,
        market_return: pd.Series,
        risk_free_rate: float = 0.065 / 252,
    ) -> pd.DataFrame:
        """Construct Fama-French factors (MKT, SMB, HML) for IDX.

        Parameters
        ----------
        returns:
            (T × N) daily returns.
        market_caps:
            (T × N) market capitalisation.
        book_to_market:
            (T × N) book-to-market ratio.
        market_return:
            (T,) market index return (e.g. IHSG).
        risk_free_rate:
            Daily risk-free rate.

        Returns
        -------
        pd.DataFrame
            Columns: MKT_IDX, SMB_IDX, HML_IDX.
        """
        factors = pd.DataFrame(index=returns.index)
        factors["MKT_IDX"] = market_return - risk_free_rate

        # For each date, classify stocks
        smb_list = []
        hml_list = []

        for date in returns.index:
            try:
                caps = market_caps.loc[date].dropna()
                bm = book_to_market.loc[date].dropna()
                rets = returns.loc[date].dropna()
            except KeyError:
                smb_list.append(0.0)
                hml_list.append(0.0)
                continue

            common = caps.index.intersection(bm.index).intersection(rets.index)
            if len(common) < 6:
                smb_list.append(0.0)
                hml_list.append(0.0)
                continue

            caps = caps[common]
            bm = bm[common]
            rets = rets[common]

            # Size split: median
            median_cap = caps.median()
            small = caps[caps <= median_cap].index
            big = caps[caps > median_cap].index

            # Value split: terciles of B/M
            low_bm = bm.quantile(1 / 3)
            high_bm = bm.quantile(2 / 3)
            growth = bm[bm <= low_bm].index
            value = bm[bm >= high_bm].index
            neutral = bm[(bm > low_bm) & (bm < high_bm)].index

            # SMB
            def mean_ret(idx: pd.Index, _rets: pd.Series = rets) -> float:
                if len(idx) == 0:
                    return 0.0
                return float(_rets[idx].mean())

            sv = mean_ret(small.intersection(value))
            sn = mean_ret(small.intersection(neutral))
            sg = mean_ret(small.intersection(growth))
            bv = mean_ret(big.intersection(value))
            bn = mean_ret(big.intersection(neutral))
            bg = mean_ret(big.intersection(growth))

            smb = ((sv + sn + sg) / 3) - ((bv + bn + bg) / 3)
            hml = ((sv + bv) / 2) - ((sg + bg) / 2)

            smb_list.append(smb)
            hml_list.append(hml)

        factors["SMB_IDX"] = smb_list
        factors["HML_IDX"] = hml_list

        return factors

    def estimate_exposures(
        self,
        stock_returns: pd.DataFrame,
        factor_returns: pd.DataFrame,
    ) -> list[FactorExposure]:
        """Estimate factor loadings via OLS regression.

        Parameters
        ----------
        stock_returns:
            (T × N) daily returns.
        factor_returns:
            (T × 3) factor returns (MKT_IDX, SMB_IDX, HML_IDX).

        Returns
        -------
        list[FactorExposure]
            Factor exposures for each stock.
        """
        exposures: list[FactorExposure] = []
        common_idx = stock_returns.index.intersection(factor_returns.index)
        factors = factor_returns.loc[common_idx]

        if len(factors) < 30:
            return exposures

        X = factors.values
        ones = np.ones((len(X), 1))
        X_with_const = np.hstack([ones, X])

        for symbol in stock_returns.columns:
            y = stock_returns[symbol].loc[common_idx].values
            valid = ~(np.isnan(y) | np.isnan(X).any(axis=1))
            if valid.sum() < 30:
                continue

            X_v = X_with_const[valid]
            y_v = y[valid]

            try:
                beta, residuals, _, _ = np.linalg.lstsq(X_v, y_v, rcond=None)
            except np.linalg.LinAlgError:
                continue

            alpha = float(beta[0])
            beta_mkt = float(beta[1])
            beta_smb = float(beta[2])
            beta_hml = float(beta[3])

            # R-squared
            y_hat = X_v @ beta
            ss_res = np.sum((y_v - y_hat) ** 2)
            ss_tot = np.sum((y_v - y_v.mean()) ** 2)
            r_sq = 1 - ss_res / ss_tot if ss_tot > 0 else 0.0

            if abs(beta_mkt) > self._max_beta:
                logger.warning(
                    "excessive_market_risk symbol=%s beta_mkt=%.2f",
                    symbol,
                    beta_mkt,
                )

            exposures.append(
                FactorExposure(
                    symbol=symbol,
                    alpha=alpha,
                    beta_mkt=beta_mkt,
                    beta_smb=beta_smb,
                    beta_hml=beta_hml,
                    r_squared=r_sq,
                )
            )

        return sorted(exposures, key=lambda e: e.alpha, reverse=True)

    def select_portfolio(
        self,
        exposures: list[FactorExposure],
    ) -> list[str]:
        """Select top-decile stocks by alpha.

        Parameters
        ----------
        exposures:
            Factor exposures sorted by alpha.

        Returns
        -------
        list[str]
            Symbols for the long portfolio.
        """
        n_select = max(1, int(len(exposures) * self._top_pct))
        return [e.symbol for e in exposures[:n_select]]
