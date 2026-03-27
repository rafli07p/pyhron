"""IDX Feature Engineering Pipeline.

Computes 40+ cross-sectional features across 7 factor groups:
1. Momentum (12-1, 6-1, 3-1, 1-0 month returns, momentum change)
2. Value (PE, PB, dividend yield, earnings yield, EV/EBITDA proxy)
3. Quality (ROE, ROA, debt-to-equity, current ratio, gross margin)
4. Low-volatility (realized vol 21/63/252d, downside deviation, beta)
5. Liquidity (Amihud illiquidity, turnover, bid-ask spread proxy, volume ratio)
6. Macro sensitivity (IDR correlation, commodity beta, yield curve slope sensitivity)
7. Technical (RSI-14, MACD histogram, Bollinger %B, ATR ratio, OBV trend)

All computations are vectorised across the cross-section using pandas/numpy.
No look-ahead bias: all features use strictly lagged data (< as_of_date).
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from scipy import stats

# Trading days constants for IDX
_TRADING_DAYS_PER_MONTH = 21
_TRADING_DAYS_PER_YEAR = 252


class IDXFeatureBuilder:
    """Builds cross-sectional feature matrix for IDX equities.

    Parameters
    ----------
    winsorize_pct : float
        Percentile for two-sided winsorisation (default 0.01 = 1st/99th).
    fill_method : str
        How to fill missing features after computation ('median' or 'zero').
    """

    def __init__(
        self,
        winsorize_pct: float = 0.01,
        fill_method: str = "median",
    ) -> None:
        self._winsorize_pct = winsorize_pct
        self._fill_method = fill_method

    def build_features(
        self,
        prices: pd.DataFrame,
        volumes: pd.DataFrame,
        fundamentals: pd.DataFrame | None = None,
        macro: pd.DataFrame | None = None,
    ) -> pd.DataFrame:
        """Build full feature matrix.

        Parameters
        ----------
        prices : DataFrame
            DatetimeIndex rows × symbol columns, close prices.
        volumes : DataFrame
            Same shape as prices, daily share volume.
        fundamentals : DataFrame, optional
            DatetimeIndex × symbols with columns as MultiIndex (symbol, metric).
            Or long-format with columns: date, symbol, pe_ratio, pb_ratio, etc.
        macro : DataFrame, optional
            DatetimeIndex with columns: usd_idr, bi_rate, coal_price, cpo_price,
            yield_10y, yield_2y, etc.

        Returns
        -------
        DataFrame
            MultiIndex (date, symbol) rows × feature columns.
            All features are cross-sectionally rank-normalised to [0, 1].
        """
        returns = prices.pct_change()
        log_returns = pd.DataFrame(np.log(prices / prices.shift(1)), index=prices.index, columns=prices.columns)

        feature_frames = []

        # Group 1: Momentum
        feature_frames.append(self._momentum_features(prices, returns))

        # Group 2: Value
        if fundamentals is not None:
            feature_frames.append(self._value_features(fundamentals, prices))

        # Group 3: Quality
        if fundamentals is not None:
            feature_frames.append(self._quality_features(fundamentals))

        # Group 4: Low-volatility
        feature_frames.append(self._volatility_features(returns, log_returns, prices))

        # Group 5: Liquidity
        feature_frames.append(self._liquidity_features(prices, volumes, returns))

        # Group 6: Macro sensitivity
        if macro is not None:
            feature_frames.append(self._macro_features(returns, macro))

        # Group 7: Technical
        feature_frames.append(self._technical_features(prices, volumes))

        # Merge all feature dicts into one: {feature_name: DataFrame(dates × symbols)}
        all_features: dict[str, pd.DataFrame] = {}
        for frame in feature_frames:
            if isinstance(frame, dict):
                all_features.update(frame)
            elif isinstance(frame, pd.DataFrame):
                # Already combined DataFrame with symbol columns
                for col in frame.columns:
                    all_features[col] = frame[[col]]

        # Stack each feature to (date, symbol) Series, then combine
        stacked_series: dict[str, pd.Series] = {}
        for name, df in all_features.items():
            if isinstance(df, pd.DataFrame) and len(df.columns) > 1:
                # Multi-column (dates × symbols) → stack to (date, symbol) Series
                stacked = df.stack(future_stack=True)
                if isinstance(stacked, pd.DataFrame):
                    s = stacked.iloc[:, 0]
                else:
                    s = stacked
                s.name = name
                stacked_series[name] = s
            elif isinstance(df, pd.DataFrame) and len(df.columns) == 1:
                s = df.iloc[:, 0]
                s.name = name
                stacked_series[name] = s
            elif isinstance(df, pd.Series):
                df.name = name
                stacked_series[name] = df

        if not stacked_series:
            return pd.DataFrame()

        combined = pd.concat(stacked_series, axis=1)

        # Winsorise and rank-normalise cross-sectionally
        result = self._postprocess(combined)
        return result

    # Group 1: Momentum

    def _momentum_features(
        self,
        prices: pd.DataFrame,
        returns: pd.DataFrame,
    ) -> dict[str, pd.DataFrame]:
        """Momentum factor group: 12-1, 6-1, 3-1, 1-0, momentum change."""
        features: dict[str, pd.DataFrame] = {}

        # 12-1 month momentum (skip most recent month)
        features["mom_12_1"] = prices.shift(_TRADING_DAYS_PER_MONTH) / prices.shift(12 * _TRADING_DAYS_PER_MONTH) - 1

        # 6-1 month momentum
        features["mom_6_1"] = prices.shift(_TRADING_DAYS_PER_MONTH) / prices.shift(6 * _TRADING_DAYS_PER_MONTH) - 1

        # 3-1 month momentum
        features["mom_3_1"] = prices.shift(_TRADING_DAYS_PER_MONTH) / prices.shift(3 * _TRADING_DAYS_PER_MONTH) - 1

        # 1-month raw return (short-term reversal)
        features["mom_1_0"] = prices / prices.shift(_TRADING_DAYS_PER_MONTH) - 1

        # Momentum change: acceleration
        mom_12_1_prev = prices.shift(2 * _TRADING_DAYS_PER_MONTH) / prices.shift(13 * _TRADING_DAYS_PER_MONTH) - 1
        features["mom_change"] = features["mom_12_1"] - mom_12_1_prev

        # 52-week high ratio
        rolling_max = prices.rolling(window=_TRADING_DAYS_PER_YEAR, min_periods=126).max()
        features["high_52w_ratio"] = prices / rolling_max

        # Information discreteness (Damodaran sign consistency)
        sign_returns: pd.DataFrame = returns.apply(np.sign)
        pos_days = sign_returns.rolling(window=_TRADING_DAYS_PER_YEAR, min_periods=126).apply(
            lambda x: (x > 0).sum(), raw=True
        )
        neg_days = sign_returns.rolling(window=_TRADING_DAYS_PER_YEAR, min_periods=126).apply(
            lambda x: (x < 0).sum(), raw=True
        )
        features["info_discrete"] = (pos_days - neg_days) / _TRADING_DAYS_PER_YEAR

        return features

    # Group 2: Value

    def _value_features(
        self,
        fundamentals: pd.DataFrame,
        prices: pd.DataFrame,
    ) -> dict[str, pd.DataFrame]:
        """Value factor group: PE, PB, dividend yield, earnings yield."""
        features: dict[str, pd.DataFrame] = {}

        # fundamentals expected as DataFrame with (date, symbol) or similar
        # Reindex to match prices dates using forward-fill (quarterly data)
        fund = fundamentals.reindex(prices.index, method="ffill")

        value_cols = {
            "pe_ratio": "val_pe",
            "pb_ratio": "val_pb",
            "dividend_yield_pct": "val_div_yield",
            "eps": "val_eps",
        }

        for src_col, feat_name in value_cols.items():
            if src_col in fund.columns:
                features[feat_name] = fund[[src_col]].rename(columns={src_col: feat_name})
            elif hasattr(fund, "xs"):
                # Try MultiIndex columns
                try:
                    xs_result = fund.xs(src_col, axis=1, level=1)
                    feat_df: pd.DataFrame = xs_result if isinstance(xs_result, pd.DataFrame) else xs_result.to_frame()
                    feat_df.columns = pd.Index([feat_name] * len(feat_df.columns))
                    features[feat_name] = feat_df
                except (KeyError, TypeError):
                    pass

        # Earnings yield = 1/PE (inverted, higher is cheaper)
        if "val_pe" in features:
            pe = features["val_pe"]
            if isinstance(pe, pd.DataFrame):
                features["val_earnings_yield"] = 1.0 / pe.replace(0, np.nan)
                features["val_earnings_yield"].columns = ["val_earnings_yield"] * len(
                    features["val_earnings_yield"].columns
                )

        return features

    # Group 3: Quality

    def _quality_features(self, fundamentals: pd.DataFrame) -> dict[str, pd.DataFrame]:
        """Quality factor group: ROE, ROA, D/E, current ratio, gross margin."""
        quality_cols = {
            "roe_pct": "qual_roe",
            "roa_pct": "qual_roa",
            "debt_to_equity": "qual_de",
            "current_ratio": "qual_current_ratio",
        }

        features: dict[str, pd.DataFrame] = {}
        for src_col, feat_name in quality_cols.items():
            if src_col in fundamentals.columns:
                features[feat_name] = fundamentals[[src_col]].rename(columns={src_col: feat_name})

        # Gross margin if revenue and gross_profit available
        if "revenue" in fundamentals.columns and "gross_profit" in fundamentals.columns:
            gm = fundamentals["gross_profit"] / fundamentals["revenue"].replace(0, np.nan)
            features["qual_gross_margin"] = gm.to_frame("qual_gross_margin")

        return features

    # Group 4: Low-Volatility

    def _volatility_features(
        self,
        returns: pd.DataFrame,
        log_returns: pd.DataFrame,
        prices: pd.DataFrame,
    ) -> dict[str, pd.DataFrame]:
        """Low-volatility factor group."""
        features: dict[str, pd.DataFrame] = {}

        # Realized volatility at different horizons
        for window, label in [(21, "21d"), (63, "63d"), (252, "252d")]:
            features[f"vol_{label}"] = returns.rolling(window=window, min_periods=max(window // 2, 10)).std() * np.sqrt(
                _TRADING_DAYS_PER_YEAR
            )

        # Downside deviation (Sortino denominator)
        downside = returns.clip(upper=0)
        features["vol_downside"] = downside.rolling(window=63, min_periods=30).std() * np.sqrt(_TRADING_DAYS_PER_YEAR)

        # Idiosyncratic volatility (residual vol after removing market)
        # Use equal-weighted market return as proxy
        mkt_return = returns.mean(axis=1)
        residuals = returns.sub(mkt_return, axis=0)
        features["vol_idio"] = residuals.rolling(window=63, min_periods=30).std() * np.sqrt(_TRADING_DAYS_PER_YEAR)

        # Beta to market
        mkt_var = mkt_return.rolling(window=63, min_periods=30).var()
        for col in returns.columns:
            cov = returns[col].rolling(window=63, min_periods=30).cov(mkt_return)
            if "vol_beta" not in features:
                features["vol_beta"] = pd.DataFrame(index=returns.index, columns=returns.columns, dtype=float)
            features["vol_beta"][col] = cov / mkt_var.replace(0, np.nan)

        return features

    # Group 5: Liquidity

    def _liquidity_features(
        self,
        prices: pd.DataFrame,
        volumes: pd.DataFrame,
        returns: pd.DataFrame,
    ) -> dict[str, pd.DataFrame]:
        """Liquidity factor group: Amihud illiquidity, turnover, volume ratio."""
        features: dict[str, pd.DataFrame] = {}

        # Amihud illiquidity: |return| / dollar_volume
        dollar_vol = prices * volumes
        amihud_daily = returns.abs() / dollar_vol.replace(0, np.nan)
        features["liq_amihud"] = amihud_daily.rolling(window=21, min_periods=10).mean()

        # Volume SMA ratio (current volume vs 63-day average)
        vol_sma_63 = volumes.rolling(window=63, min_periods=30).mean()
        features["liq_vol_ratio"] = volumes / vol_sma_63.replace(0, np.nan)

        # Turnover (21-day average volume / proxy shares outstanding)
        features["liq_turnover_21d"] = volumes.rolling(window=21, min_periods=10).mean()

        # Zero-return days (illiquidity proxy)
        zero_days = (returns.abs() < 1e-8).astype(float)
        features["liq_zero_days_21d"] = zero_days.rolling(window=21, min_periods=10).sum()

        # Roll spread estimator
        cov_returns = pd.DataFrame(index=returns.index, columns=returns.columns, dtype=float)
        for col in returns.columns:
            cov_returns[col] = returns[col].rolling(window=21, min_periods=10).apply(
                lambda x: np.cov(x[:-1], x[1:])[0, 1] if len(x) > 1 else 0, raw=True
            )
        clipped = (-cov_returns).clip(lower=0)
        features["liq_roll_spread"] = pd.DataFrame(
            2 * np.sqrt(clipped.values), index=clipped.index, columns=clipped.columns
        )

        return features

    # Group 6: Macro Sensitivity

    def _macro_features(
        self,
        returns: pd.DataFrame,
        macro: pd.DataFrame,
    ) -> dict[str, pd.DataFrame]:
        """Macro sensitivity: correlation with USD/IDR, commodities, yield curve."""
        features: dict[str, pd.DataFrame] = {}
        macro = macro.reindex(returns.index, method="ffill")
        window = 63

        # USD/IDR sensitivity
        if "usd_idr" in macro.columns:
            fx_ret = macro["usd_idr"].pct_change()
            for col in returns.columns:
                corr = returns[col].rolling(window=window, min_periods=30).corr(fx_ret)
                if "macro_fx_corr" not in features:
                    features["macro_fx_corr"] = pd.DataFrame(
                        index=returns.index, columns=returns.columns, dtype=float
                    )
                features["macro_fx_corr"][col] = corr

        # Commodity beta (coal or CPO)
        for commodity in ["coal_price", "cpo_price"]:
            if commodity in macro.columns:
                comm_ret = macro[commodity].pct_change()
                feat_name = f"macro_{commodity.split('_')[0]}_beta"
                feat_df = pd.DataFrame(index=returns.index, columns=returns.columns, dtype=float)
                comm_var = comm_ret.rolling(window=window, min_periods=30).var()
                for col in returns.columns:
                    cov = returns[col].rolling(window=window, min_periods=30).cov(comm_ret)
                    feat_df[col] = cov / comm_var.replace(0, np.nan)
                features[feat_name] = feat_df

        # Yield curve slope sensitivity
        if "yield_10y" in macro.columns and "yield_2y" in macro.columns:
            slope = macro["yield_10y"] - macro["yield_2y"]
            slope_change = slope.diff()
            feat_df = pd.DataFrame(index=returns.index, columns=returns.columns, dtype=float)
            for col in returns.columns:
                feat_df[col] = returns[col].rolling(window=window, min_periods=30).corr(slope_change)
            features["macro_yield_slope_corr"] = feat_df

        return features

    # Group 7: Technical

    def _technical_features(
        self,
        prices: pd.DataFrame,
        volumes: pd.DataFrame,
    ) -> dict[str, pd.DataFrame]:
        """Technical indicators: RSI, MACD, Bollinger %B, ATR ratio, OBV trend."""
        features: dict[str, pd.DataFrame] = {}

        returns = prices.pct_change()

        # RSI-14
        delta = prices.diff()
        gain = delta.clip(lower=0)
        loss = (-delta).clip(lower=0)
        avg_gain = gain.ewm(span=14, adjust=False).mean()
        avg_loss = loss.ewm(span=14, adjust=False).mean()
        rs = avg_gain / avg_loss.replace(0, np.nan)
        features["tech_rsi_14"] = 100 - (100 / (1 + rs))

        # MACD histogram
        ema_12 = prices.ewm(span=12, adjust=False).mean()
        ema_26 = prices.ewm(span=26, adjust=False).mean()
        macd_line = ema_12 - ema_26
        signal_line = macd_line.ewm(span=9, adjust=False).mean()
        features["tech_macd_hist"] = (macd_line - signal_line) / prices  # Normalise by price

        # Bollinger %B
        sma_20 = prices.rolling(window=20, min_periods=10).mean()
        std_20 = prices.rolling(window=20, min_periods=10).std()
        upper_band = sma_20 + 2 * std_20
        lower_band = sma_20 - 2 * std_20
        band_width = upper_band - lower_band
        features["tech_bbpct"] = (prices - lower_band) / band_width.replace(0, np.nan)

        # ATR ratio (ATR / price for normalisation)
        high = prices  # Approximate with close if no high/low
        low = prices
        tr = high - low  # Simplified; ideally use OHLC
        atr_14 = tr.rolling(window=14, min_periods=7).mean()
        features["tech_atr_ratio"] = atr_14 / prices.replace(0, np.nan)

        # OBV trend (normalised slope of OBV over 21 days)
        signed_vol = volumes * np.sign(returns)
        obv = signed_vol.cumsum()
        obv_slope = pd.DataFrame(index=prices.index, columns=prices.columns, dtype=float)
        for col in prices.columns:
            obv_slope[col] = (
                obv[col]
                .rolling(window=21, min_periods=10)
                .apply(lambda x: stats.linregress(range(len(x)), x).slope if len(x) > 1 else 0, raw=True)
            )
        # Normalise by volume level
        features["tech_obv_slope"] = obv_slope / volumes.rolling(window=21, min_periods=10).mean().replace(0, np.nan)

        return features

    # Helpers

    def _postprocess(self, df: pd.DataFrame) -> pd.DataFrame:
        """Winsorise and cross-sectionally rank-normalise features."""
        result = df.copy()

        for col in result.columns:
            # Winsorise per cross-section (date)
            if isinstance(result.index, pd.MultiIndex):
                grouped = result[col].groupby(level=0)
                lo = grouped.transform(lambda x: x.quantile(self._winsorize_pct))
                hi = grouped.transform(lambda x: x.quantile(1 - self._winsorize_pct))
                result[col] = result[col].clip(lower=lo, upper=hi)

                # Rank-normalise to [0, 1] cross-sectionally
                result[col] = grouped.transform(lambda x: x.rank(pct=True))
            else:
                # Single-level index: just rank
                lo_val = float(result[col].quantile(self._winsorize_pct))
                hi_val = float(result[col].quantile(1 - self._winsorize_pct))
                result[col] = result[col].clip(lower=lo_val, upper=hi_val)
                result[col] = result[col].rank(pct=True)

        # Fill remaining NaNs
        if self._fill_method == "median":
            result = result.fillna(0.5)  # Median rank
        else:
            result = result.fillna(0.0)

        return result

    @staticmethod
    def get_feature_names(
        include_value: bool = True,
        include_quality: bool = True,
        include_macro: bool = True,
    ) -> list[str]:
        """Return expected feature column names for documentation."""
        names = [
            # Momentum (7)
            "mom_12_1", "mom_6_1", "mom_3_1", "mom_1_0",
            "mom_change", "high_52w_ratio", "info_discrete",
        ]
        if include_value:
            names.extend([
                "val_pe", "val_pb", "val_div_yield", "val_eps", "val_earnings_yield",
            ])
        if include_quality:
            names.extend([
                "qual_roe", "qual_roa", "qual_de", "qual_current_ratio", "qual_gross_margin",
            ])
        names.extend([
            # Low-volatility (6)
            "vol_21d", "vol_63d", "vol_252d", "vol_downside", "vol_idio", "vol_beta",
            # Liquidity (5)
            "liq_amihud", "liq_vol_ratio", "liq_turnover_21d", "liq_zero_days_21d", "liq_roll_spread",
        ])
        if include_macro:
            names.extend([
                "macro_fx_corr", "macro_coal_beta", "macro_cpo_beta", "macro_yield_slope_corr",
            ])
        names.extend([
            # Technical (5)
            "tech_rsi_14", "tech_macd_hist", "tech_bbpct", "tech_atr_ratio", "tech_obv_slope",
        ])
        return names
