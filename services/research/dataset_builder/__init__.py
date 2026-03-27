"""Dataset builder for the Pyhron trading platform.

Fetches market data from real APIs (Polygon, yfinance), engineers
features (returns, volatility, volume profile, technical indicators),
and outputs pandas or Dask DataFrames for downstream research.
"""

from __future__ import annotations

import asyncio
from collections.abc import Callable
from datetime import date, datetime
from typing import Any, Literal

import dask.dataframe as dd
import numpy as np
import pandas as pd
import structlog
import yfinance as yf

logger = structlog.get_logger(__name__)


# Feature engineering functions

def _add_returns(df: pd.DataFrame, windows: list[int] | None = None) -> pd.DataFrame:
    """Add log and simple return columns for various windows."""
    windows = windows or [1, 5, 21, 63, 126, 252]
    for w in windows:
        df[f"return_{w}d"] = df["close"].pct_change(w)
        df[f"log_return_{w}d"] = np.log(df["close"] / df["close"].shift(w))
    return df


def _add_volatility(df: pd.DataFrame, windows: list[int] | None = None) -> pd.DataFrame:
    """Add realised volatility features."""
    windows = windows or [5, 21, 63]
    daily_ret = df["close"].pct_change()
    for w in windows:
        df[f"volatility_{w}d"] = daily_ret.rolling(window=w).std() * np.sqrt(252)
    # Parkinson volatility (using high/low)
    if "high" in df.columns and "low" in df.columns:
        hl_ratio = np.log(df["high"] / df["low"])
        for w in windows:
            df[f"parkinson_vol_{w}d"] = (
                hl_ratio.pow(2).rolling(window=w).mean() / (4 * np.log(2))
            ).pow(0.5) * np.sqrt(252)
    return df


def _add_volume_profile(df: pd.DataFrame, windows: list[int] | None = None) -> pd.DataFrame:
    """Add volume-based features."""
    windows = windows or [5, 21, 63]
    if "volume" not in df.columns:
        return df
    for w in windows:
        df[f"volume_sma_{w}d"] = df["volume"].rolling(window=w).mean()
        df[f"volume_ratio_{w}d"] = df["volume"] / df[f"volume_sma_{w}d"]
    # On-Balance Volume (OBV)
    direction = np.sign(df["close"].diff())
    df["obv"] = (direction * df["volume"]).cumsum()
    return df


def _add_technical_indicators(df: pd.DataFrame) -> pd.DataFrame:
    """Add standard technical indicators."""
    close = df["close"]

    # Simple moving averages
    for w in [10, 20, 50, 200]:
        df[f"sma_{w}"] = close.rolling(window=w).mean()
        df[f"close_to_sma_{w}"] = close / df[f"sma_{w}"]

    # Exponential moving averages
    for w in [12, 26, 50]:
        df[f"ema_{w}"] = close.ewm(span=w, adjust=False).mean()

    # MACD
    ema12 = close.ewm(span=12, adjust=False).mean()
    ema26 = close.ewm(span=26, adjust=False).mean()
    df["macd"] = ema12 - ema26
    df["macd_signal"] = df["macd"].ewm(span=9, adjust=False).mean()
    df["macd_histogram"] = df["macd"] - df["macd_signal"]

    # RSI
    delta = close.diff()
    gain = delta.where(delta > 0, 0.0)
    loss = -delta.where(delta < 0, 0.0)
    avg_gain = gain.rolling(window=14).mean()
    avg_loss = loss.rolling(window=14).mean()
    rs = avg_gain / avg_loss.replace(0, np.nan)
    df["rsi_14"] = 100 - (100 / (1 + rs))

    # Bollinger Bands
    sma20 = close.rolling(window=20).mean()
    std20 = close.rolling(window=20).std()
    df["bb_upper"] = sma20 + 2 * std20
    df["bb_lower"] = sma20 - 2 * std20
    df["bb_width"] = (df["bb_upper"] - df["bb_lower"]) / sma20
    df["bb_position"] = (close - df["bb_lower"]) / (df["bb_upper"] - df["bb_lower"])

    # Average True Range (ATR)
    if "high" in df.columns and "low" in df.columns:
        high_low = df["high"] - df["low"]
        high_close = (df["high"] - close.shift(1)).abs()
        low_close = (df["low"] - close.shift(1)).abs()
        true_range = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
        df["atr_14"] = true_range.rolling(window=14).mean()

    # Stochastic %K / %D
    if "high" in df.columns and "low" in df.columns:
        low14 = df["low"].rolling(window=14).min()
        high14 = df["high"].rolling(window=14).max()
        df["stoch_k"] = (close - low14) / (high14 - low14) * 100
        df["stoch_d"] = df["stoch_k"].rolling(window=3).mean()

    return df


# Data fetching

async def _fetch_ohlcv_yfinance(
    symbol: str,
    start_date: date,
    end_date: date,
) -> pd.DataFrame:
    """Fetch OHLCV data for a single symbol from yfinance."""
    loop = asyncio.get_running_loop()

    def _download() -> pd.DataFrame:
        ticker = yf.Ticker(symbol)
        hist = ticker.history(start=str(start_date), end=str(end_date), auto_adjust=True)
        if hist.empty:
            return pd.DataFrame()
        hist.columns = [c.lower() for c in hist.columns]
        hist["symbol"] = symbol
        return hist

    return await loop.run_in_executor(None, _download)


async def _fetch_ohlcv_polygon(
    symbol: str,
    start_date: date,
    end_date: date,
    api_key: str,
) -> pd.DataFrame:
    """Fetch OHLCV data for a single symbol from Polygon.io."""
    import aiohttp

    async with aiohttp.ClientSession() as session:
        url = (
            f"https://api.polygon.io/v2/aggs/ticker/{symbol}/range/1/day/"
            f"{start_date}/{end_date}?adjusted=true&sort=asc&apiKey={api_key}"
        )
        async with session.get(url) as resp:
            if resp.status != 200:
                return pd.DataFrame()
            body = await resp.json()
            results = body.get("results", [])

    if not results:
        return pd.DataFrame()

    df = pd.DataFrame(results)
    df["date"] = pd.to_datetime(df["t"], unit="ms")
    df = df.set_index("date")
    df = df.rename(columns={"o": "open", "h": "high", "l": "low", "c": "close", "v": "volume"})
    df["symbol"] = symbol
    return df[["open", "high", "low", "close", "volume", "symbol"]]


# Dataset builder

# Map of supported feature groups to their engineering functions
_FEATURE_MAP: dict[str, Callable[[pd.DataFrame], pd.DataFrame]] = {
    "returns": _add_returns,
    "volatility": _add_volatility,
    "volume_profile": _add_volume_profile,
    "technical_indicators": _add_technical_indicators,
}


class DatasetBuilder:
    """Builds feature-engineered datasets from real market data APIs.

    Fetches OHLCV data from Polygon.io (preferred) or yfinance
    (fallback), applies feature engineering, and returns a pandas
    or Dask DataFrame.

    Parameters
    ----------
    polygon_api_key:
        Optional Polygon.io API key.
    use_dask:
        If ``True``, return a Dask DataFrame.
    dask_npartitions:
        Number of Dask partitions.
    """

    def __init__(
        self,
        polygon_api_key: str | None = None,
        use_dask: bool = False,
        dask_npartitions: int = 8,
    ) -> None:
        self._polygon_key = polygon_api_key
        self._use_dask = use_dask
        self._dask_npartitions = dask_npartitions
        self._log = logger.bind(component="DatasetBuilder")

    async def build_dataset(
        self,
        symbols: list[str],
        features: list[str],
        start: date,
        end: date,
        tenant_id: str = "default",
    ) -> pd.DataFrame | dd.DataFrame:
        """Build a feature-rich dataset from market data.

        Parameters
        ----------
        symbols:
            List of ticker symbols to include.
        features:
            Feature groups to engineer.  Supported: ``"returns"``,
            ``"volatility"``, ``"volume_profile"``,
            ``"technical_indicators"``.
        start:
            Dataset start date.
        end:
            Dataset end date.
        tenant_id:
            Tenant identifier (for logging/auditing).

        Returns
        -------
        pd.DataFrame | dd.DataFrame
            Feature-engineered dataset with a MultiIndex (date, symbol)
            or concatenated by symbol.
        """
        self._log.info(
            "build_dataset",
            symbols=symbols,
            features=features,
            start=str(start),
            end=str(end),
            tenant_id=tenant_id,
        )

        # 1. Fetch raw OHLCV data for all symbols concurrently
        tasks = [self._fetch_symbol(sym, start, end) for sym in symbols]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        frames: list[pd.DataFrame] = []
        for sym, result in zip(symbols, results):
            if isinstance(result, BaseException):
                self._log.warning("fetch_failed", symbol=sym, error=str(result))
                continue
            if result.empty:
                self._log.warning("no_data", symbol=sym)
                continue
            frames.append(result)

        if not frames:
            self._log.error("no_data_for_any_symbol", symbols=symbols)
            return pd.DataFrame()

        # 2. Apply feature engineering per symbol
        engineered: list[pd.DataFrame] = []
        for df in frames:
            df = df.copy()
            # Forward-fill missing data
            df = df.ffill()
            for feat in features:
                fn = _FEATURE_MAP.get(feat)
                if fn is not None:
                    df = fn(df)
                else:
                    self._log.warning("unknown_feature", feature=feat)
            engineered.append(df)

        # 3. Combine
        combined = pd.concat(engineered, axis=0)
        combined = combined.sort_index()

        self._log.info(
            "dataset_built",
            rows=len(combined),
            columns=len(combined.columns),
            symbols=len(frames),
            tenant_id=tenant_id,
        )

        # 4. Optionally convert to Dask
        if self._use_dask:
            return dd.from_pandas(combined, npartitions=self._dask_npartitions)

        return combined

    async def _fetch_symbol(
        self,
        symbol: str,
        start_date: date,
        end_date: date,
    ) -> pd.DataFrame:
        """Fetch OHLCV for a single symbol, trying Polygon then yfinance."""
        if self._polygon_key:
            try:
                df = await _fetch_ohlcv_polygon(symbol, start_date, end_date, self._polygon_key)
                if not df.empty:
                    return df
            except Exception:
                self._log.warning("polygon_fallback", symbol=symbol)

        return await _fetch_ohlcv_yfinance(symbol, start_date, end_date)


__all__ = [
    "DatasetBuilder",
]
