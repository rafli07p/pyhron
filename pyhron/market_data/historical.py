"""Historical data loader for the Pyhron trading platform.

Loads OHLCV data from yfinance with local CSV caching to avoid
redundant API calls during backtest iterations.
"""

from __future__ import annotations

import csv
import logging
from datetime import date
from decimal import Decimal
from pathlib import Path

from pyhron.market_data.client import OHLCVBar

logger = logging.getLogger(__name__)


class HistoricalDataLoader:
    """Load historical OHLCV bars with disk caching.

    Parameters
    ----------
    cache_dir:
        Directory for local CSV cache files.
    source:
        Data source identifier (currently only ``"yfinance"``).
    """

    def __init__(self, cache_dir: str = ".cache/historical", source: str = "yfinance") -> None:
        self.cache_dir = cache_dir
        self.source = source

    def load(
        self, symbols: list[str], start_date: date, end_date: date
    ) -> dict[str, list[OHLCVBar]]:
        """Load OHLCV bars for multiple symbols.

        Checks the local CSV cache first. On cache miss, fetches from
        yfinance and writes to cache for future runs.

        Returns
        -------
        dict:
            Mapping of symbol -> list of OHLCVBar sorted by date ascending.
        """
        result: dict[str, list[OHLCVBar]] = {}
        for symbol in symbols:
            bars = self._load_cached(symbol, start_date, end_date)
            if bars is not None:
                result[symbol] = bars
                logger.info("historical.cache_hit", extra={"symbol": symbol, "bars": len(bars)})
            else:
                bars = self._fetch_and_cache(symbol, start_date, end_date)
                result[symbol] = bars
                logger.info("historical.fetched", extra={"symbol": symbol, "bars": len(bars)})
        return result

    def _cache_path(self, symbol: str, start_date: date, end_date: date) -> Path:
        """Build the cache file path for a given query."""
        safe_symbol = symbol.replace("/", "_").replace(".", "_")
        filename = f"{safe_symbol}_{start_date.isoformat()}_{end_date.isoformat()}.csv"
        return Path(self.cache_dir) / filename

    def _load_cached(self, symbol: str, start_date: date, end_date: date) -> list[OHLCVBar] | None:
        """Attempt to load bars from the CSV cache."""
        path = self._cache_path(symbol, start_date, end_date)
        if not path.exists():
            return None

        bars: list[OHLCVBar] = []
        with open(path, newline="") as f:
            reader = csv.DictReader(f)
            for row in reader:
                bars.append(
                    OHLCVBar(
                        date=date.fromisoformat(row["date"]),
                        open=Decimal(row["open"]),
                        high=Decimal(row["high"]),
                        low=Decimal(row["low"]),
                        close=Decimal(row["close"]),
                        volume=int(row["volume"]),
                    )
                )
        return bars

    def _fetch_and_cache(self, symbol: str, start_date: date, end_date: date) -> list[OHLCVBar]:
        """Fetch from yfinance and persist to CSV cache."""
        import yfinance as yf

        ticker = yf.Ticker(symbol)
        df = ticker.history(
            start=start_date.strftime("%Y-%m-%d"),
            end=end_date.strftime("%Y-%m-%d"),
            interval="1d",
        )

        if df is None or df.empty:
            return []

        bars: list[OHLCVBar] = []
        for idx, row in df.iterrows():
            bar_date = idx.date() if hasattr(idx, "date") else idx
            bars.append(
                OHLCVBar(
                    date=bar_date,
                    open=Decimal(str(round(row["Open"], 4))),
                    high=Decimal(str(round(row["High"], 4))),
                    low=Decimal(str(round(row["Low"], 4))),
                    close=Decimal(str(round(row["Close"], 4))),
                    volume=int(row.get("Volume", 0)),
                )
            )

        # Write to cache
        self._write_cache(symbol, start_date, end_date, bars)
        return bars

    def _write_cache(
        self, symbol: str, start_date: date, end_date: date, bars: list[OHLCVBar]
    ) -> None:
        """Write bars to the CSV cache."""
        path = self._cache_path(symbol, start_date, end_date)
        path.parent.mkdir(parents=True, exist_ok=True)

        with open(path, "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=["date", "open", "high", "low", "close", "volume"])
            writer.writeheader()
            for bar in bars:
                writer.writerow({
                    "date": bar.date.isoformat(),
                    "open": str(bar.open),
                    "high": str(bar.high),
                    "low": str(bar.low),
                    "close": str(bar.close),
                    "volume": bar.volume,
                })
