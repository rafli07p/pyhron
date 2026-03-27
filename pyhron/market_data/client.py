"""Market data client for the Pyhron trading platform.

Fetches real-time quotes and historical OHLCV bars using yfinance
as the primary data source. Designed for IDX equities and global
instruments.
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from datetime import UTC, date, datetime
from decimal import Decimal

from pyhron.shared.schemas.tick import TickData

logger = logging.getLogger(__name__)


@dataclass
class OHLCVBar:
    date: date
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    volume: int


_INTERVAL_MAP = {
    "1m": "1m",
    "5m": "5m",
    "15m": "15m",
    "1h": "1h",
    "1d": "1d",
    "1wk": "1wk",
    "1mo": "1mo",
}


class MarketDataClient:
    """Async market data client backed by yfinance.

    Parameters
    ----------
    api_key:
        API key (reserved for premium data providers).
    base_url:
        Base URL (reserved for REST-based providers).
    timeout:
        HTTP timeout in seconds.
    """

    def __init__(self, api_key: str = "", base_url: str = "", timeout: int = 30) -> None:
        self.api_key = api_key
        self.base_url = base_url
        self.timeout = timeout
        self._closed = False

    async def get_latest_quote(self, symbol: str) -> TickData | None:
        """Fetch the latest quote for a single symbol.

        Uses yfinance fast_info and bid/ask from ticker info.
        Returns None if the symbol is invalid or data unavailable.
        """
        if self._closed:
            raise RuntimeError("Client is closed")

        loop = asyncio.get_running_loop()
        try:
            return await loop.run_in_executor(None, self._fetch_quote_sync, symbol)
        except Exception:
            logger.exception("market_data.quote_failed", extra={"symbol": symbol})
            return None

    async def get_latest_quotes(self, symbols: list[str]) -> list[TickData]:
        """Fetch latest quotes for multiple symbols concurrently."""
        if self._closed:
            raise RuntimeError("Client is closed")

        tasks = [self.get_latest_quote(s) for s in symbols]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        return [r for r in results if isinstance(r, TickData)]

    async def get_historical_bars(
        self, symbol: str, start: datetime, end: datetime, interval: str = "1d"
    ) -> list[OHLCVBar]:
        """Fetch historical OHLCV bars for a symbol.

        Parameters
        ----------
        symbol:
            Instrument symbol (e.g. "BBCA.JK").
        start:
            Start datetime (inclusive).
        end:
            End datetime (inclusive).
        interval:
            Bar interval ("1d", "1h", "5m", etc).
        """
        if self._closed:
            raise RuntimeError("Client is closed")

        yf_interval = _INTERVAL_MAP.get(interval, "1d")
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, self._fetch_bars_sync, symbol, start, end, yf_interval)

    async def close(self) -> None:
        """Mark client as closed."""
        self._closed = True

    def _fetch_quote_sync(self, symbol: str) -> TickData | None:
        """Synchronous quote fetch via yfinance."""
        import yfinance as yf

        ticker = yf.Ticker(symbol)
        info = ticker.info
        if not info or "regularMarketPrice" not in info:
            return None

        price = Decimal(str(info.get("regularMarketPrice", 0)))
        bid = Decimal(str(info.get("bid", 0)))
        ask = Decimal(str(info.get("ask", 0)))
        volume = int(info.get("regularMarketVolume", 0) or 0)
        exchange = str(info.get("exchange", ""))

        # Ensure bid <= ask; fallback to price if not available
        if bid <= 0:
            bid = price
        if ask <= 0:
            ask = price
        if bid > ask:
            bid, ask = ask, bid

        return TickData(
            symbol=symbol,
            price=price,
            volume=volume,
            bid=bid,
            ask=ask,
            timestamp=datetime.now(UTC),
            exchange=exchange,
        )

    def _fetch_bars_sync(self, symbol: str, start: datetime, end: datetime, interval: str) -> list[OHLCVBar]:
        """Synchronous OHLCV fetch via yfinance."""
        import yfinance as yf

        ticker = yf.Ticker(symbol)
        df = ticker.history(
            start=start.strftime("%Y-%m-%d"),
            end=end.strftime("%Y-%m-%d"),
            interval=interval,
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
        return bars
