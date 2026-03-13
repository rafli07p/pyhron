"""Async CCXT adapter for crypto market data relevant to IDX analysis.

Primary use cases:
- BTC/USDT as global risk sentiment proxy
- Gold (PAXG/USDT) as safe haven proxy
- Stablecoin premiums as USD/IDR stress indicator
"""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal, InvalidOperation
from typing import Any

import ccxt.async_support as ccxt_async

from data_platform.adapters.eodhd_adapter import EODHDOHLCVRecord
from shared.structured_json_logger import get_logger

logger = get_logger(__name__)


class CCXTAdapter:
    """Async CCXT adapter for crypto market data relevant to IDX analysis."""

    def __init__(
        self,
        exchange_id: str = "binance",
        api_key: str | None = None,
        secret: str | None = None,
    ) -> None:
        self._exchange_id = exchange_id
        self._api_key = api_key
        self._secret = secret
        self._exchanges: dict[str, ccxt_async.Exchange] = {}

    async def _get_exchange(self, exchange_id: str) -> ccxt_async.Exchange:
        if exchange_id not in self._exchanges:
            exchange_class = getattr(ccxt_async, exchange_id)
            config: dict[str, str | bool] = {"enableRateLimit": True}
            if self._api_key:
                config["apiKey"] = self._api_key
            if self._secret:
                config["secret"] = self._secret
            self._exchanges[exchange_id] = exchange_class(config)
        return self._exchanges[exchange_id]

    async def get_ohlcv(
        self,
        exchange_id: str,
        symbol: str,
        timeframe: str,
        since: datetime | None = None,
        limit: int = 500,
    ) -> list[EODHDOHLCVRecord]:
        """Fetch OHLCV candles from a crypto exchange."""
        exchange = await self._get_exchange(exchange_id)
        since_ms = int(since.timestamp() * 1000) if since else None

        try:
            candles = await exchange.fetch_ohlcv(symbol, timeframe, since=since_ms, limit=limit)
        except Exception as e:
            logger.warning("ccxt_fetch_failed", exchange=exchange_id, symbol=symbol, error=str(e))
            return []

        records: list[EODHDOHLCVRecord] = []
        base_symbol = symbol.replace("/", "_")
        for candle in candles:
            try:
                ts, o, h, low, c, vol = candle[:6]
                candle_date = datetime.fromtimestamp(ts / 1000, tz=UTC).date()
                records.append(
                    EODHDOHLCVRecord(
                        symbol=base_symbol,
                        date=candle_date,
                        open=Decimal(str(o)),
                        high=Decimal(str(h)),
                        low=Decimal(str(low)),
                        close=Decimal(str(c)),
                        adjusted_close=Decimal(str(c)),
                        volume=int(vol) if vol else 0,
                        source=f"ccxt_{exchange_id}",
                    )
                )
            except (InvalidOperation, ValueError, TypeError) as e:
                logger.warning("skipping_ccxt_candle", symbol=symbol, error=str(e))
        return records

    async def get_ticker(
        self,
        exchange_id: str,
        symbol: str,
    ) -> dict[str, Any]:
        """Fetch latest ticker data from a crypto exchange."""
        exchange = await self._get_exchange(exchange_id)
        try:
            return await exchange.fetch_ticker(symbol)  # type: ignore[no-any-return]
        except Exception as e:
            logger.warning("ccxt_ticker_failed", exchange=exchange_id, symbol=symbol, error=str(e))
            return {}

    async def close(self) -> None:
        """Close all open exchange connections."""
        for exchange in self._exchanges.values():
            await exchange.close()
        self._exchanges.clear()
