"""Exchange adapters for market data retrieval.

Provides a plugin-style adapter architecture with a ``BaseAdapter`` ABC
and concrete implementations for:

* **MassiveAdapter** -- Polygon.io REST API via ``polygon.RESTClient``
* **YFinanceAdapter** -- ``yfinance`` for equities including IDX (``.JK``)
* **CCXTAdapter** -- ``ccxt`` for crypto / multi-exchange
* **IDXAdapter** -- placeholder for OHLC.dev / Invezgo via ``httpx``

An automatic fallback chain (Massive -> yfinance -> CCXT) is exposed via
``FallbackChain``.
"""

from __future__ import annotations

import asyncio
import os
from abc import ABC, abstractmethod
from datetime import datetime
from decimal import Decimal
from typing import Any, Optional, Sequence

import ccxt
import httpx
import structlog
import yfinance as yf
from dotenv import load_dotenv
from polygon import RESTClient
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from shared.schemas.market_events import BarEvent, Exchange, QuoteEvent, TradeEvent

load_dotenv()

logger = structlog.get_logger(__name__)

_POLYGON_API_KEY = os.getenv("POLYGON_API_KEY", "")
_MAX_RETRIES = int(os.getenv("ADAPTER_MAX_RETRIES", "4"))


# ---------------------------------------------------------------------------
# Base adapter ABC
# ---------------------------------------------------------------------------

class BaseAdapter(ABC):
    """Abstract base for all exchange data adapters.

    Every adapter must implement ``get_bars``, ``get_quotes``, and
    ``get_trades``.  Subclass this to add new data sources as plugins.
    """

    name: str = "base"

    @abstractmethod
    async def get_bars(
        self,
        symbol: str,
        start: str,
        end: str,
        interval: str = "1d",
        tenant_id: str = "",
    ) -> list[BarEvent]:
        """Fetch OHLCV bars for *symbol* between *start* and *end*."""

    @abstractmethod
    async def get_quotes(
        self,
        symbol: str,
        tenant_id: str = "",
    ) -> list[QuoteEvent]:
        """Fetch recent quotes (top-of-book) for *symbol*."""

    @abstractmethod
    async def get_trades(
        self,
        symbol: str,
        start: str,
        end: str,
        tenant_id: str = "",
    ) -> list[TradeEvent]:
        """Fetch individual trades for *symbol* in the given range."""

    async def health_check(self) -> bool:
        """Return ``True`` if this adapter can serve requests right now."""
        return True


# ---------------------------------------------------------------------------
# MassiveAdapter (Polygon.io)
# ---------------------------------------------------------------------------

class MassiveAdapter(BaseAdapter):
    """Polygon.io REST adapter with built-in rate-limit handling.

    Parameters
    ----------
    api_key:
        Polygon API key.  Falls back to ``POLYGON_API_KEY`` env var.
    """

    name = "polygon"

    def __init__(self, api_key: Optional[str] = None) -> None:
        self._api_key = api_key or _POLYGON_API_KEY
        self._client: Optional[RESTClient] = None
        self._log = logger.bind(adapter=self.name)

    def _get_client(self) -> RESTClient:
        if self._client is None:
            if not self._api_key:
                raise RuntimeError("POLYGON_API_KEY not configured")
            self._client = RESTClient(api_key=self._api_key)
        return self._client

    @retry(
        retry=retry_if_exception_type((ConnectionError, TimeoutError, OSError)),
        stop=stop_after_attempt(_MAX_RETRIES),
        wait=wait_exponential(multiplier=1, min=1, max=30),
        reraise=True,
    )
    async def get_bars(
        self,
        symbol: str,
        start: str,
        end: str,
        interval: str = "1d",
        tenant_id: str = "",
    ) -> list[BarEvent]:
        client = self._get_client()

        timespan_map: dict[str, tuple[int, str]] = {
            "1m": (1, "minute"),
            "5m": (5, "minute"),
            "15m": (15, "minute"),
            "1h": (1, "hour"),
            "1d": (1, "day"),
            "1w": (1, "week"),
        }
        multiplier, timespan = timespan_map.get(interval, (1, "day"))

        loop = asyncio.get_running_loop()
        aggs = await loop.run_in_executor(
            None,
            lambda: list(
                client.list_aggs(
                    ticker=symbol,
                    multiplier=multiplier,
                    timespan=timespan,
                    from_=start,
                    to=end,
                    limit=50_000,
                )
            ),
        )

        interval_seconds_map = {"minute": 60, "hour": 3600, "day": 86400, "week": 604800}
        interval_secs = interval_seconds_map.get(timespan, 86400) * multiplier

        bars: list[BarEvent] = []
        for agg in aggs:
            bars.append(
                BarEvent(
                    symbol=symbol,
                    timestamp=datetime.utcfromtimestamp(agg.timestamp / 1000),
                    exchange=Exchange.OTHER,
                    tenant_id=tenant_id,
                    open=Decimal(str(agg.open)),
                    high=Decimal(str(agg.high)),
                    low=Decimal(str(agg.low)),
                    close=Decimal(str(agg.close)),
                    volume=Decimal(str(agg.volume)),
                    vwap=Decimal(str(agg.vwap)) if agg.vwap else None,
                    bar_count=getattr(agg, "transactions", None),
                    interval_seconds=interval_secs,
                )
            )
        self._log.info("polygon_bars_fetched", symbol=symbol, count=len(bars))
        return bars

    @retry(
        retry=retry_if_exception_type((ConnectionError, TimeoutError, OSError)),
        stop=stop_after_attempt(_MAX_RETRIES),
        wait=wait_exponential(multiplier=1, min=1, max=30),
        reraise=True,
    )
    async def get_quotes(
        self,
        symbol: str,
        tenant_id: str = "",
    ) -> list[QuoteEvent]:
        client = self._get_client()
        loop = asyncio.get_running_loop()
        nbbo = await loop.run_in_executor(
            None,
            lambda: client.get_last_quote(symbol),
        )
        quote = QuoteEvent(
            symbol=symbol,
            timestamp=datetime.utcnow(),
            exchange=Exchange.OTHER,
            tenant_id=tenant_id,
            bid=Decimal(str(nbbo.bid_price)) if nbbo.bid_price else Decimal("0"),
            ask=Decimal(str(nbbo.ask_price)) if nbbo.ask_price else Decimal("0"),
            bid_size=Decimal(str(nbbo.bid_size)) if nbbo.bid_size else Decimal("0"),
            ask_size=Decimal(str(nbbo.ask_size)) if nbbo.ask_size else Decimal("0"),
        )
        return [quote]

    @retry(
        retry=retry_if_exception_type((ConnectionError, TimeoutError, OSError)),
        stop=stop_after_attempt(_MAX_RETRIES),
        wait=wait_exponential(multiplier=1, min=1, max=30),
        reraise=True,
    )
    async def get_trades(
        self,
        symbol: str,
        start: str,
        end: str,
        tenant_id: str = "",
    ) -> list[TradeEvent]:
        client = self._get_client()
        loop = asyncio.get_running_loop()
        raw_trades = await loop.run_in_executor(
            None,
            lambda: list(client.list_trades(symbol, timestamp_gte=start, timestamp_lte=end, limit=5000)),
        )
        trades: list[TradeEvent] = []
        for t in raw_trades:
            ts_ns = t.sip_timestamp or t.participant_timestamp or 0
            trades.append(
                TradeEvent(
                    symbol=symbol,
                    timestamp=datetime.utcfromtimestamp(ts_ns / 1e9),
                    exchange=Exchange.OTHER,
                    tenant_id=tenant_id,
                    price=Decimal(str(t.price)),
                    volume=Decimal(str(t.size)),
                    trade_id=str(getattr(t, "id", "")),
                )
            )
        self._log.info("polygon_trades_fetched", symbol=symbol, count=len(trades))
        return trades

    async def health_check(self) -> bool:
        try:
            self._get_client()
            return True
        except RuntimeError:
            return False


# ---------------------------------------------------------------------------
# YFinanceAdapter
# ---------------------------------------------------------------------------

class YFinanceAdapter(BaseAdapter):
    """yfinance adapter for equities and IDX symbols (.JK suffix).

    Supports Indonesian stocks like ``BBCA.JK`` and indices like ``^JKSE``.
    """

    name = "yfinance"

    def __init__(self) -> None:
        self._log = logger.bind(adapter=self.name)

    async def get_bars(
        self,
        symbol: str,
        start: str,
        end: str,
        interval: str = "1d",
        tenant_id: str = "",
    ) -> list[BarEvent]:
        loop = asyncio.get_running_loop()

        def _download():
            ticker = yf.Ticker(symbol)
            return ticker.history(start=start, end=end, interval=interval, auto_adjust=True)

        df = await loop.run_in_executor(None, _download)

        interval_seconds_map = {
            "1m": 60, "2m": 120, "5m": 300, "15m": 900,
            "30m": 1800, "60m": 3600, "90m": 5400,
            "1h": 3600, "1d": 86400, "5d": 432000,
            "1wk": 604800, "1mo": 2592000, "3mo": 7776000,
        }
        int_secs = interval_seconds_map.get(interval, 86400)

        bars: list[BarEvent] = []
        for ts, row in df.iterrows():
            bars.append(
                BarEvent(
                    symbol=symbol,
                    timestamp=ts.to_pydatetime(),
                    exchange=Exchange.OTHER,
                    tenant_id=tenant_id,
                    open=Decimal(str(round(row["Open"], 8))),
                    high=Decimal(str(round(row["High"], 8))),
                    low=Decimal(str(round(row["Low"], 8))),
                    close=Decimal(str(round(row["Close"], 8))),
                    volume=Decimal(str(int(row["Volume"]))),
                    interval_seconds=int_secs,
                )
            )
        self._log.info("yfinance_bars_fetched", symbol=symbol, count=len(bars))
        return bars

    async def get_quotes(
        self,
        symbol: str,
        tenant_id: str = "",
    ) -> list[QuoteEvent]:
        loop = asyncio.get_running_loop()

        def _fetch():
            ticker = yf.Ticker(symbol)
            return ticker.info

        info = await loop.run_in_executor(None, _fetch)
        bid = Decimal(str(info.get("bid", 0)))
        ask = Decimal(str(info.get("ask", 0)))
        return [
            QuoteEvent(
                symbol=symbol,
                timestamp=datetime.utcnow(),
                exchange=Exchange.OTHER,
                tenant_id=tenant_id,
                bid=bid,
                ask=ask,
                bid_size=Decimal(str(info.get("bidSize", 0))),
                ask_size=Decimal(str(info.get("askSize", 0))),
            )
        ]

    async def get_trades(
        self,
        symbol: str,
        start: str,
        end: str,
        tenant_id: str = "",
    ) -> list[TradeEvent]:
        # yfinance does not provide tick-level trade data;
        # return empty list and let the fallback chain try another adapter.
        self._log.debug("yfinance_trades_not_supported", symbol=symbol)
        return []


# ---------------------------------------------------------------------------
# CCXTAdapter
# ---------------------------------------------------------------------------

class CCXTAdapter(BaseAdapter):
    """CCXT adapter for crypto exchanges and multi-exchange support.

    Parameters
    ----------
    exchange_id:
        CCXT exchange identifier (e.g. ``binance``, ``coinbasepro``).
    """

    name = "ccxt"

    def __init__(self, exchange_id: str = "binance") -> None:
        self.exchange_id = exchange_id
        self._exchange: Any = None
        self._log = logger.bind(adapter=self.name, exchange=exchange_id)

    def _get_exchange(self) -> Any:
        if self._exchange is None:
            exchange_class = getattr(ccxt, self.exchange_id)
            api_key = os.getenv(f"CCXT_{self.exchange_id.upper()}_API_KEY", "")
            secret = os.getenv(f"CCXT_{self.exchange_id.upper()}_SECRET", "")
            config: dict[str, Any] = {"enableRateLimit": True}
            if api_key:
                config["apiKey"] = api_key
            if secret:
                config["secret"] = secret
            self._exchange = exchange_class(config)
        return self._exchange

    @retry(
        retry=retry_if_exception_type((ccxt.NetworkError, ccxt.ExchangeNotAvailable)),
        stop=stop_after_attempt(_MAX_RETRIES),
        wait=wait_exponential(multiplier=1, min=1, max=30),
        reraise=True,
    )
    async def get_bars(
        self,
        symbol: str,
        start: str,
        end: str,
        interval: str = "1d",
        tenant_id: str = "",
    ) -> list[BarEvent]:
        exchange = self._get_exchange()
        loop = asyncio.get_running_loop()

        since_ms = int(datetime.fromisoformat(start).timestamp() * 1000)

        # CCXT timeframe mapping
        tf_map = {"1m": "1m", "5m": "5m", "15m": "15m", "1h": "1h", "1d": "1d", "1w": "1w"}
        timeframe = tf_map.get(interval, "1d")

        interval_seconds_map = {
            "1m": 60, "5m": 300, "15m": 900,
            "1h": 3600, "1d": 86400, "1w": 604800,
        }
        int_secs = interval_seconds_map.get(timeframe, 86400)

        ohlcv_data = await loop.run_in_executor(
            None,
            lambda: exchange.fetch_ohlcv(symbol, timeframe=timeframe, since=since_ms, limit=1000),
        )

        end_ms = int(datetime.fromisoformat(end).timestamp() * 1000)
        bars: list[BarEvent] = []
        for candle in ohlcv_data:
            ts_ms, o, h, l_, c, v = candle
            if ts_ms > end_ms:
                break
            bars.append(
                BarEvent(
                    symbol=symbol,
                    timestamp=datetime.utcfromtimestamp(ts_ms / 1000),
                    exchange=Exchange.OTHER,
                    tenant_id=tenant_id,
                    open=Decimal(str(o)),
                    high=Decimal(str(h)),
                    low=Decimal(str(l_)),
                    close=Decimal(str(c)),
                    volume=Decimal(str(v)),
                    interval_seconds=int_secs,
                )
            )
        self._log.info("ccxt_bars_fetched", symbol=symbol, count=len(bars))
        return bars

    @retry(
        retry=retry_if_exception_type((ccxt.NetworkError, ccxt.ExchangeNotAvailable)),
        stop=stop_after_attempt(_MAX_RETRIES),
        wait=wait_exponential(multiplier=1, min=1, max=30),
        reraise=True,
    )
    async def get_quotes(
        self,
        symbol: str,
        tenant_id: str = "",
    ) -> list[QuoteEvent]:
        exchange = self._get_exchange()
        loop = asyncio.get_running_loop()
        order_book = await loop.run_in_executor(
            None,
            lambda: exchange.fetch_order_book(symbol, limit=1),
        )
        bid = Decimal(str(order_book["bids"][0][0])) if order_book.get("bids") else Decimal("0")
        ask = Decimal(str(order_book["asks"][0][0])) if order_book.get("asks") else Decimal("0")
        bid_size = Decimal(str(order_book["bids"][0][1])) if order_book.get("bids") else Decimal("0")
        ask_size = Decimal(str(order_book["asks"][0][1])) if order_book.get("asks") else Decimal("0")
        return [
            QuoteEvent(
                symbol=symbol,
                timestamp=datetime.utcnow(),
                exchange=Exchange.OTHER,
                tenant_id=tenant_id,
                bid=bid,
                ask=ask,
                bid_size=bid_size,
                ask_size=ask_size,
            )
        ]

    @retry(
        retry=retry_if_exception_type((ccxt.NetworkError, ccxt.ExchangeNotAvailable)),
        stop=stop_after_attempt(_MAX_RETRIES),
        wait=wait_exponential(multiplier=1, min=1, max=30),
        reraise=True,
    )
    async def get_trades(
        self,
        symbol: str,
        start: str,
        end: str,
        tenant_id: str = "",
    ) -> list[TradeEvent]:
        exchange = self._get_exchange()
        loop = asyncio.get_running_loop()
        since_ms = int(datetime.fromisoformat(start).timestamp() * 1000)
        raw_trades = await loop.run_in_executor(
            None,
            lambda: exchange.fetch_trades(symbol, since=since_ms, limit=1000),
        )
        end_ms = int(datetime.fromisoformat(end).timestamp() * 1000)
        side_map = {"buy": "BUY", "sell": "SELL"}
        trades: list[TradeEvent] = []
        for t in raw_trades:
            if t["timestamp"] > end_ms:
                break
            trades.append(
                TradeEvent(
                    symbol=symbol,
                    timestamp=datetime.utcfromtimestamp(t["timestamp"] / 1000),
                    exchange=Exchange.OTHER,
                    tenant_id=tenant_id,
                    price=Decimal(str(t["price"])),
                    volume=Decimal(str(t["amount"])),
                    trade_id=str(t.get("id", "")),
                    aggressor_side=side_map.get(t.get("side", ""), "UNKNOWN"),
                )
            )
        self._log.info("ccxt_trades_fetched", symbol=symbol, count=len(trades))
        return trades

    async def health_check(self) -> bool:
        try:
            exchange = self._get_exchange()
            loop = asyncio.get_running_loop()
            await loop.run_in_executor(None, exchange.load_markets)
            return True
        except Exception:
            return False


# ---------------------------------------------------------------------------
# IDXAdapter (OHLC.dev / Invezgo placeholder via httpx)
# ---------------------------------------------------------------------------

class IDXAdapter(BaseAdapter):
    """Placeholder adapter for Indonesian exchange data via OHLC.dev / Invezgo.

    Uses ``httpx`` for HTTP calls.  Base URL and API key are configurable
    via environment variables ``IDX_API_BASE_URL`` and ``IDX_API_KEY``.
    """

    name = "idx"

    def __init__(self) -> None:
        self._base_url = os.getenv("IDX_API_BASE_URL", "https://api.ohlc.dev/v1")
        self._api_key = os.getenv("IDX_API_KEY", "")
        self._log = logger.bind(adapter=self.name)

    def _headers(self) -> dict[str, str]:
        headers: dict[str, str] = {"Accept": "application/json"}
        if self._api_key:
            headers["Authorization"] = f"Bearer {self._api_key}"
        return headers

    @retry(
        retry=retry_if_exception_type((httpx.ConnectError, httpx.TimeoutException)),
        stop=stop_after_attempt(_MAX_RETRIES),
        wait=wait_exponential(multiplier=1, min=1, max=30),
        reraise=True,
    )
    async def get_bars(
        self,
        symbol: str,
        start: str,
        end: str,
        interval: str = "1d",
        tenant_id: str = "",
    ) -> list[BarEvent]:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.get(
                f"{self._base_url}/ohlcv",
                params={"symbol": symbol, "from": start, "to": end, "interval": interval},
                headers=self._headers(),
            )
            resp.raise_for_status()
            data = resp.json()

        bars: list[BarEvent] = []
        for row in data.get("data", data.get("results", [])):
            ts = row.get("timestamp") or row.get("date") or row.get("t")
            if isinstance(ts, (int, float)):
                dt = datetime.utcfromtimestamp(ts / 1000 if ts > 1e12 else ts)
            else:
                dt = datetime.fromisoformat(str(ts))
            bars.append(
                BarEvent(
                    symbol=symbol,
                    timestamp=dt,
                    exchange=Exchange.OTHER,
                    tenant_id=tenant_id,
                    open=Decimal(str(row.get("open", row.get("o", 0)))),
                    high=Decimal(str(row.get("high", row.get("h", 0)))),
                    low=Decimal(str(row.get("low", row.get("l", 0)))),
                    close=Decimal(str(row.get("close", row.get("c", 0)))),
                    volume=Decimal(str(row.get("volume", row.get("v", 0)))),
                    interval_seconds=86400,
                )
            )
        self._log.info("idx_bars_fetched", symbol=symbol, count=len(bars))
        return bars

    async def get_quotes(
        self,
        symbol: str,
        tenant_id: str = "",
    ) -> list[QuoteEvent]:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.get(
                f"{self._base_url}/quote",
                params={"symbol": symbol},
                headers=self._headers(),
            )
            resp.raise_for_status()
            data = resp.json()

        bid = Decimal(str(data.get("bid", 0)))
        ask = Decimal(str(data.get("ask", 0)))
        return [
            QuoteEvent(
                symbol=symbol,
                timestamp=datetime.utcnow(),
                exchange=Exchange.OTHER,
                tenant_id=tenant_id,
                bid=bid,
                ask=ask,
                bid_size=Decimal(str(data.get("bidSize", 0))),
                ask_size=Decimal(str(data.get("askSize", 0))),
            )
        ]

    async def get_trades(
        self,
        symbol: str,
        start: str,
        end: str,
        tenant_id: str = "",
    ) -> list[TradeEvent]:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.get(
                f"{self._base_url}/trades",
                params={"symbol": symbol, "from": start, "to": end},
                headers=self._headers(),
            )
            resp.raise_for_status()
            data = resp.json()

        trades: list[TradeEvent] = []
        for row in data.get("data", data.get("results", [])):
            ts = row.get("timestamp", row.get("t", 0))
            if isinstance(ts, (int, float)):
                dt = datetime.utcfromtimestamp(ts / 1000 if ts > 1e12 else ts)
            else:
                dt = datetime.fromisoformat(str(ts))
            trades.append(
                TradeEvent(
                    symbol=symbol,
                    timestamp=dt,
                    exchange=Exchange.OTHER,
                    tenant_id=tenant_id,
                    price=Decimal(str(row.get("price", row.get("p", 0)))),
                    volume=Decimal(str(row.get("volume", row.get("s", 0)))),
                    trade_id=str(row.get("id", "")),
                )
            )
        self._log.info("idx_trades_fetched", symbol=symbol, count=len(trades))
        return trades

    async def health_check(self) -> bool:
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(f"{self._base_url}/health", headers=self._headers())
                return resp.status_code < 400
        except Exception:
            return False


# ---------------------------------------------------------------------------
# FallbackChain
# ---------------------------------------------------------------------------

class FallbackChain:
    """Automatic fallback chain across adapters.

    Tries adapters in order (default: Massive -> yfinance -> CCXT) and
    returns the first successful result.

    Parameters
    ----------
    adapters:
        Ordered sequence of adapters to try.  If ``None``, uses the
        default chain ``[MassiveAdapter, YFinanceAdapter, CCXTAdapter]``.
    """

    def __init__(self, adapters: Optional[Sequence[BaseAdapter]] = None) -> None:
        self.adapters: list[BaseAdapter] = list(adapters) if adapters else [
            MassiveAdapter(),
            YFinanceAdapter(),
            CCXTAdapter(),
        ]
        self._log = logger.bind(service="fallback_chain")

    async def get_bars(
        self,
        symbol: str,
        start: str,
        end: str,
        interval: str = "1d",
        tenant_id: str = "",
    ) -> list[BarEvent]:
        last_exc: Optional[Exception] = None
        for adapter in self.adapters:
            try:
                bars = await adapter.get_bars(symbol, start, end, interval, tenant_id)
                if bars:
                    self._log.info(
                        "fallback_chain_success",
                        adapter=adapter.name,
                        symbol=symbol,
                        count=len(bars),
                    )
                    return bars
            except Exception as exc:
                self._log.warning(
                    "fallback_chain_adapter_failed",
                    adapter=adapter.name,
                    symbol=symbol,
                    error=str(exc),
                )
                last_exc = exc
        if last_exc:
            raise last_exc
        return []

    async def get_quotes(
        self,
        symbol: str,
        tenant_id: str = "",
    ) -> list[QuoteEvent]:
        last_exc: Optional[Exception] = None
        for adapter in self.adapters:
            try:
                quotes = await adapter.get_quotes(symbol, tenant_id)
                if quotes:
                    return quotes
            except Exception as exc:
                self._log.warning(
                    "fallback_chain_quote_failed",
                    adapter=adapter.name,
                    error=str(exc),
                )
                last_exc = exc
        if last_exc:
            raise last_exc
        return []

    async def get_trades(
        self,
        symbol: str,
        start: str,
        end: str,
        tenant_id: str = "",
    ) -> list[TradeEvent]:
        last_exc: Optional[Exception] = None
        for adapter in self.adapters:
            try:
                trades = await adapter.get_trades(symbol, start, end, tenant_id)
                if trades:
                    return trades
            except Exception as exc:
                self._log.warning(
                    "fallback_chain_trade_failed",
                    adapter=adapter.name,
                    error=str(exc),
                )
                last_exc = exc
        if last_exc:
            raise last_exc
        return []


__all__ = [
    "BaseAdapter",
    "MassiveAdapter",
    "YFinanceAdapter",
    "CCXTAdapter",
    "IDXAdapter",
    "FallbackChain",
]
