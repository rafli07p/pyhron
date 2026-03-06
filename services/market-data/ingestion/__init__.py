"""Market data ingestion service.

Primary source: Polygon.io via the ``polygon`` Python client.
Fallback: ``yfinance`` for equities (including Indonesian .JK symbols).
Includes Redis caching, tenacity retry with exponential backoff, and
structured logging via structlog.
"""

from __future__ import annotations

import asyncio
import os
from datetime import date, datetime
from decimal import Decimal
from typing import TYPE_CHECKING, Any, Optional, Sequence

import redis.asyncio as aioredis
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

from shared.schemas.market_events import BarEvent, Exchange, TickEvent, TradeEvent

if TYPE_CHECKING:
    import pandas as pd

load_dotenv()

logger = structlog.get_logger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
_POLYGON_API_KEY = os.getenv("POLYGON_API_KEY", "")
_REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
_CACHE_TTL_SECONDS = int(os.getenv("MARKET_DATA_CACHE_TTL", "300"))
_MAX_RETRIES = int(os.getenv("MARKET_DATA_MAX_RETRIES", "5"))

# Indonesian exchange symbols use .JK suffix on yfinance
_IDX_SUFFIX = ".JK"


class MarketDataIngestionService:
    """Ingest historical and real-time market data from multiple providers.

    Parameters
    ----------
    tenant_id:
        Tenant identifier for multi-tenancy isolation.
    polygon_api_key:
        Polygon.io API key.  Falls back to ``POLYGON_API_KEY`` env var.
    redis_url:
        Redis connection URL for caching.  Falls back to ``REDIS_URL`` env var.
    """

    def __init__(
        self,
        tenant_id: str,
        polygon_api_key: Optional[str] = None,
        redis_url: Optional[str] = None,
    ) -> None:
        self.tenant_id = tenant_id
        self._polygon_key = polygon_api_key or _POLYGON_API_KEY
        self._redis_url = redis_url or _REDIS_URL

        # Polygon REST client (lazy; created on first use)
        self._polygon: Optional[RESTClient] = None
        self._redis: Optional[aioredis.Redis] = None
        self._stream_task: Optional[asyncio.Task[None]] = None
        self._streaming = False

        self._log = logger.bind(tenant_id=tenant_id, service="ingestion")

    # ------------------------------------------------------------------
    # Lifecycle helpers
    # ------------------------------------------------------------------

    def _get_polygon_client(self) -> RESTClient:
        """Return a (lazily created) Polygon REST client."""
        if self._polygon is None:
            if not self._polygon_key:
                raise RuntimeError(
                    "POLYGON_API_KEY is not set. Provide it via constructor or env var."
                )
            self._polygon = RESTClient(api_key=self._polygon_key)
            self._log.info("polygon_client_created")
        return self._polygon

    async def _get_redis(self) -> aioredis.Redis:
        """Return a (lazily created) async Redis connection."""
        if self._redis is None:
            self._redis = aioredis.from_url(
                self._redis_url, decode_responses=True
            )
            self._log.info("redis_connected", url=self._redis_url)
        return self._redis

    # ------------------------------------------------------------------
    # Cache helpers
    # ------------------------------------------------------------------

    async def _cache_get(self, key: str) -> Optional[str]:
        r = await self._get_redis()
        return await r.get(key)

    async def _cache_set(self, key: str, value: str, ttl: int = _CACHE_TTL_SECONDS) -> None:
        r = await self._get_redis()
        await r.set(key, value, ex=ttl)

    # ------------------------------------------------------------------
    # Historical ingestion
    # ------------------------------------------------------------------

    @retry(
        retry=retry_if_exception_type((ConnectionError, TimeoutError, OSError)),
        stop=stop_after_attempt(_MAX_RETRIES),
        wait=wait_exponential(multiplier=1, min=1, max=60),
        reraise=True,
    )
    async def ingest_historical(
        self,
        symbol: str,
        start: date | str,
        end: date | str,
        timespan: str = "day",
        multiplier: int = 1,
    ) -> list[BarEvent]:
        """Fetch historical OHLCV bars.

        Attempts Polygon.io first; falls back to yfinance on failure.

        Parameters
        ----------
        symbol:
            Ticker symbol.  Use ``.JK`` suffix for IDX stocks (e.g. ``BBCA.JK``).
        start / end:
            Date range (inclusive).
        timespan:
            Bar timespan (``minute``, ``hour``, ``day``, ``week``, ``month``).
        multiplier:
            Timespan multiplier (e.g. ``5`` with ``minute`` = 5-min bars).

        Returns
        -------
        list[BarEvent]
            Normalised bar events.
        """
        start_str = start if isinstance(start, str) else start.isoformat()
        end_str = end if isinstance(end, str) else end.isoformat()

        cache_key = f"mkt:hist:{self.tenant_id}:{symbol}:{start_str}:{end_str}:{timespan}:{multiplier}"
        cached = await self._cache_get(cache_key)
        if cached is not None:
            self._log.debug("cache_hit", symbol=symbol, key=cache_key)
            import json

            return [BarEvent.model_validate_json(b) for b in json.loads(cached)]

        # --- Try Polygon.io first ---
        if self._polygon_key and not symbol.endswith(_IDX_SUFFIX):
            try:
                bars = await self._fetch_polygon_bars(
                    symbol, start_str, end_str, timespan, multiplier
                )
                self._log.info(
                    "polygon_historical_fetched",
                    symbol=symbol,
                    bar_count=len(bars),
                )
                await self._persist_cache(cache_key, bars)
                return bars
            except Exception:
                self._log.warning(
                    "polygon_historical_failed_falling_back",
                    symbol=symbol,
                    exc_info=True,
                )

        # --- Fallback: yfinance ---
        bars = await self._fetch_yfinance_bars(symbol, start_str, end_str)
        self._log.info(
            "yfinance_historical_fetched",
            symbol=symbol,
            bar_count=len(bars),
        )
        await self._persist_cache(cache_key, bars)
        return bars

    # ------------------------------------------------------------------
    # Polygon helpers
    # ------------------------------------------------------------------

    async def _fetch_polygon_bars(
        self,
        symbol: str,
        start: str,
        end: str,
        timespan: str,
        multiplier: int,
    ) -> list[BarEvent]:
        """Fetch bars from Polygon.io REST API."""
        client = self._get_polygon_client()

        # Polygon client is synchronous; run in executor
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

        interval_map = {
            "minute": 60,
            "hour": 3600,
            "day": 86400,
            "week": 604800,
            "month": 2592000,
        }
        interval_seconds = interval_map.get(timespan, 60) * multiplier

        bars: list[BarEvent] = []
        for agg in aggs:
            bars.append(
                BarEvent(
                    symbol=symbol,
                    timestamp=datetime.utcfromtimestamp(agg.timestamp / 1000),
                    exchange=Exchange.OTHER,
                    tenant_id=self.tenant_id,
                    open=Decimal(str(agg.open)),
                    high=Decimal(str(agg.high)),
                    low=Decimal(str(agg.low)),
                    close=Decimal(str(agg.close)),
                    volume=Decimal(str(agg.volume)),
                    vwap=Decimal(str(agg.vwap)) if agg.vwap else None,
                    bar_count=agg.transactions if hasattr(agg, "transactions") else None,
                    interval_seconds=interval_seconds,
                )
            )
        return bars

    # ------------------------------------------------------------------
    # yfinance helpers
    # ------------------------------------------------------------------

    async def _fetch_yfinance_bars(
        self,
        symbol: str,
        start: str,
        end: str,
    ) -> list[BarEvent]:
        """Fetch bars from yfinance (supports IDX .JK symbols)."""
        loop = asyncio.get_running_loop()

        def _download() -> "pd.DataFrame":
            ticker = yf.Ticker(symbol)
            return ticker.history(start=start, end=end, auto_adjust=True)

        df = await loop.run_in_executor(None, _download)

        bars: list[BarEvent] = []
        for ts, row in df.iterrows():
            bars.append(
                BarEvent(
                    symbol=symbol,
                    timestamp=ts.to_pydatetime(),
                    exchange=Exchange.OTHER,
                    tenant_id=self.tenant_id,
                    open=Decimal(str(round(row["Open"], 8))),
                    high=Decimal(str(round(row["High"], 8))),
                    low=Decimal(str(round(row["Low"], 8))),
                    close=Decimal(str(round(row["Close"], 8))),
                    volume=Decimal(str(int(row["Volume"]))),
                    interval_seconds=86400,
                )
            )
        return bars

    # ------------------------------------------------------------------
    # Real-time streaming
    # ------------------------------------------------------------------

    async def start_realtime_stream(
        self,
        symbols: Sequence[str],
        on_bar: Any | None = None,
    ) -> None:
        """Start a background real-time streaming task.

        Uses Polygon WebSocket for US equities.  Publishes received events
        to Redis pub/sub channel ``mkt:realtime:{tenant_id}``.

        Parameters
        ----------
        symbols:
            Symbols to subscribe to.
        on_bar:
            Optional async callback ``(BarEvent) -> None``.
        """
        if self._streaming:
            self._log.warning("stream_already_running")
            return

        self._streaming = True

        # Import streaming module to avoid circular deps at module level
        from services.market_data.streaming import StreamingService

        streamer = StreamingService(
            tenant_id=self.tenant_id,
            polygon_api_key=self._polygon_key,
            redis_url=self._redis_url,
        )
        await streamer.connect()
        await streamer.subscribe(list(symbols))

        async def _run() -> None:
            try:
                while self._streaming:
                    await asyncio.sleep(0.1)
            finally:
                await streamer.disconnect()

        self._stream_task = asyncio.create_task(_run())
        self._log.info("realtime_stream_started", symbols=list(symbols))

    async def stop_stream(self) -> None:
        """Stop the background real-time streaming task."""
        self._streaming = False
        if self._stream_task is not None:
            self._stream_task.cancel()
            try:
                await self._stream_task
            except asyncio.CancelledError:
                pass
            self._stream_task = None
        self._log.info("realtime_stream_stopped")

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    async def _persist_cache(self, key: str, bars: list[BarEvent]) -> None:
        """Serialise bars to JSON and store in Redis."""
        import json

        payload = json.dumps([b.model_dump_json() for b in bars])
        await self._cache_set(key, payload)

    async def close(self) -> None:
        """Release resources."""
        await self.stop_stream()
        if self._redis is not None:
            await self._redis.aclose()
            self._redis = None
        self._polygon = None
        self._log.info("ingestion_service_closed")


__all__ = ["MarketDataIngestionService"]
