"""Async HTTP adapter for the EODHD Financial Data API.

Base URL: https://eodhd.com/api
Authentication: api_token query parameter from config

Rate limits:
  Free tier:    20 requests per minute
  Paid tier:    100,000 requests per day, no per-minute limit
Apply conservative throttling regardless of tier: max 5 req/s.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from datetime import date
from decimal import Decimal, InvalidOperation

import httpx

from shared.structured_json_logger import get_logger

logger = get_logger(__name__)


class EODHDAPIError(Exception):
    """Non-retriable EODHD API error."""

    def __init__(self, status_code: int, message: str) -> None:
        self.status_code = status_code
        super().__init__(f"EODHD API error {status_code}: {message}")


class EODHDRateLimitError(EODHDAPIError):
    """Rate limit exceeded (HTTP 429)."""

    def __init__(self) -> None:
        super().__init__(429, "Rate limit exceeded")


class EODHDAuthError(EODHDAPIError):
    """Authentication failure (HTTP 401/403)."""

    def __init__(self, status_code: int = 401) -> None:
        super().__init__(status_code, "Authentication failed")


class EODHDNotFoundError(EODHDAPIError):
    """Resource not found (HTTP 404)."""

    def __init__(self, resource: str) -> None:
        super().__init__(404, f"Not found: {resource}")


@dataclass
class EODHDOHLCVRecord:
    symbol: str
    date: date
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    adjusted_close: Decimal
    volume: int
    source: str = "eodhd"


@dataclass
class EODHDDividendRecord:
    symbol: str
    ex_date: date
    payment_date: date | None
    dividend_idr: Decimal
    dividend_type: str


@dataclass
class EODHDSplitRecord:
    symbol: str
    date: date
    split_ratio: Decimal


@dataclass
class EODHDInstrumentRecord:
    symbol: str
    name: str
    exchange: str
    asset_type: str
    isin: str | None
    currency: str


class EODHDAdapter:
    """Async HTTP adapter for the EODHD Financial Data API."""

    BASE_URL = "https://eodhd.com/api"
    MAX_RPS = 5
    TIMEOUT_SECONDS = 30
    MAX_RETRIES = 3
    RETRY_BACKOFF_BASE = 2

    def __init__(self, api_token: str, session: httpx.AsyncClient) -> None:
        self._api_token = api_token
        self._session = session
        self._rate_semaphore = asyncio.Semaphore(self.MAX_RPS)
        self._rate_lock = asyncio.Lock()
        self._last_request_time: float = 0.0

    async def get_eod_data(
        self,
        symbol: str,
        exchange: str = "IDX",
        date_from: date | None = None,
        date_to: date | None = None,
        adjusted: bool = True,
    ) -> list[EODHDOHLCVRecord]:
        """Fetch end-of-day OHLCV bars for a single symbol."""
        params: dict[str, str] = {"fmt": "json"}
        if date_from:
            params["from"] = date_from.isoformat()
        if date_to:
            params["to"] = date_to.isoformat()

        ticker = f"{symbol}.{exchange}" if "." not in symbol else symbol
        data = await self._request(f"/eod/{ticker}", params)
        if not isinstance(data, list):
            return []

        records: list[EODHDOHLCVRecord] = []
        for row in data:
            try:
                record = EODHDOHLCVRecord(
                    symbol=symbol.split(".")[0],
                    date=date.fromisoformat(str(row["date"])),
                    open=Decimal(str(row["open"])),
                    high=Decimal(str(row["high"])),
                    low=Decimal(str(row["low"])),
                    close=Decimal(str(row["close"])),
                    adjusted_close=Decimal(str(row.get("adjusted_close", row["close"]))),
                    volume=int(row.get("volume", 0)),
                    source="eodhd",
                )
                records.append(record)
            except (KeyError, InvalidOperation, ValueError) as e:
                logger.warning("skipping_malformed_eodhd_row", symbol=symbol, error=str(e))
        return records

    async def get_fundamentals(
        self,
        symbol: str,
        exchange: str = "IDX",
        filter_field: str | None = None,
    ) -> dict:
        """Fetch fundamental data (financials, ratios, general info)."""
        params: dict[str, str] = {"fmt": "json"}
        if filter_field:
            params["filter"] = filter_field

        ticker = f"{symbol}.{exchange}" if "." not in symbol else symbol
        data = await self._request(f"/fundamentals/{ticker}", params)
        return data if isinstance(data, dict) else {}

    async def get_dividends(
        self,
        symbol: str,
        exchange: str = "IDX",
        date_from: date | None = None,
    ) -> list[EODHDDividendRecord]:
        """Fetch dividend history for a symbol."""
        params: dict[str, str] = {"fmt": "json"}
        if date_from:
            params["from"] = date_from.isoformat()

        ticker = f"{symbol}.{exchange}" if "." not in symbol else symbol
        data = await self._request(f"/div/{ticker}", params)
        if not isinstance(data, list):
            return []

        records: list[EODHDDividendRecord] = []
        for row in data:
            try:
                payment_raw = row.get("paymentDate")
                payment_dt = (
                    date.fromisoformat(str(payment_raw)) if payment_raw and payment_raw != "0000-00-00" else None
                )
                records.append(
                    EODHDDividendRecord(
                        symbol=symbol.split(".")[0],
                        ex_date=date.fromisoformat(str(row["date"])),
                        payment_date=payment_dt,
                        dividend_idr=Decimal(str(row["value"])),
                        dividend_type=row.get("type", "cash"),
                    )
                )
            except (KeyError, InvalidOperation, ValueError) as e:
                logger.warning("skipping_malformed_dividend_row", symbol=symbol, error=str(e))
        return records

    async def get_splits(
        self,
        symbol: str,
        exchange: str = "IDX",
    ) -> list[EODHDSplitRecord]:
        """Fetch stock split history for a symbol."""
        params: dict[str, str] = {"fmt": "json"}
        ticker = f"{symbol}.{exchange}" if "." not in symbol else symbol
        data = await self._request(f"/splits/{ticker}", params)
        if not isinstance(data, list):
            return []

        records: list[EODHDSplitRecord] = []
        for row in data:
            try:
                split_str = str(row["split"])
                parts = split_str.split("/")
                if len(parts) == 2:
                    ratio = Decimal(parts[0]) / Decimal(parts[1])
                else:
                    ratio = Decimal(split_str)
                records.append(
                    EODHDSplitRecord(
                        symbol=symbol.split(".")[0],
                        date=date.fromisoformat(str(row["date"])),
                        split_ratio=ratio,
                    )
                )
            except (KeyError, InvalidOperation, ValueError, ZeroDivisionError) as e:
                logger.warning("skipping_malformed_split_row", symbol=symbol, error=str(e))
        return records

    async def get_exchange_symbols(
        self,
        exchange: str = "IDX",
    ) -> list[EODHDInstrumentRecord]:
        """Fetch full instrument universe for the exchange."""
        data = await self._request(f"/exchange-symbol-list/{exchange}", {"fmt": "json"})
        if not isinstance(data, list):
            return []

        records: list[EODHDInstrumentRecord] = []
        for row in data:
            try:
                records.append(
                    EODHDInstrumentRecord(
                        symbol=str(row["Code"]),
                        name=str(row.get("Name", "")),
                        exchange=str(row.get("Exchange", exchange)),
                        asset_type=str(row.get("Type", "Common Stock")),
                        isin=row.get("Isin") or None,
                        currency=str(row.get("Currency", "IDR")),
                    )
                )
            except (KeyError, ValueError) as e:
                logger.warning("skipping_malformed_instrument_row", error=str(e))
        return records

    async def get_bulk_eod(
        self,
        exchange: str = "IDX",
        trade_date: date | None = None,
    ) -> list[EODHDOHLCVRecord]:
        """Fetch all EOD bars for the exchange in a single request."""
        params: dict[str, str] = {"fmt": "json", "type": "eod"}
        if trade_date:
            params["date"] = trade_date.isoformat()

        data = await self._request(f"/eod-bulk-last-day/{exchange}", params)
        if not isinstance(data, list):
            return []

        records: list[EODHDOHLCVRecord] = []
        for row in data:
            try:
                records.append(
                    EODHDOHLCVRecord(
                        symbol=str(row["code"]),
                        date=date.fromisoformat(str(row["date"])),
                        open=Decimal(str(row["open"])),
                        high=Decimal(str(row["high"])),
                        low=Decimal(str(row["low"])),
                        close=Decimal(str(row["close"])),
                        adjusted_close=Decimal(str(row.get("adjusted_close", row["close"]))),
                        volume=int(row.get("volume", 0)),
                        source="eodhd",
                    )
                )
            except (KeyError, InvalidOperation, ValueError) as e:
                logger.warning("skipping_malformed_bulk_row", error=str(e))
        return records

    async def _request(
        self,
        endpoint: str,
        params: dict[str, str],
    ) -> dict | list:
        """Execute HTTP GET with retry, rate limiting, and error handling."""
        params["api_token"] = self._api_token
        url = f"{self.BASE_URL}{endpoint}"

        for attempt in range(self.MAX_RETRIES):
            async with self._rate_semaphore:
                # Enforce minimum spacing between requests
                async with self._rate_lock:
                    now = asyncio.get_event_loop().time()
                    min_interval = 1.0 / self.MAX_RPS
                    elapsed = now - self._last_request_time
                    if elapsed < min_interval:
                        await asyncio.sleep(min_interval - elapsed)
                    self._last_request_time = asyncio.get_event_loop().time()

                try:
                    response = await self._session.get(
                        url,
                        params=params,
                        timeout=self.TIMEOUT_SECONDS,
                    )
                except httpx.TimeoutException:
                    if attempt < self.MAX_RETRIES - 1:
                        wait = self.RETRY_BACKOFF_BASE ** (attempt + 1)
                        logger.warning("eodhd_timeout_retry", endpoint=endpoint, attempt=attempt, wait_s=wait)
                        await asyncio.sleep(wait)
                        continue
                    raise EODHDAPIError(0, f"Timeout after {self.MAX_RETRIES} attempts: {endpoint}")
                except httpx.HTTPError as e:
                    if attempt < self.MAX_RETRIES - 1:
                        wait = self.RETRY_BACKOFF_BASE ** (attempt + 1)
                        logger.warning("eodhd_http_error_retry", endpoint=endpoint, error=str(e), attempt=attempt)
                        await asyncio.sleep(wait)
                        continue
                    raise EODHDAPIError(0, f"HTTP error after {self.MAX_RETRIES} attempts: {e}")

                if response.status_code == 200:
                    return response.json()
                if response.status_code == 429:
                    if attempt < self.MAX_RETRIES - 1:
                        wait = self.RETRY_BACKOFF_BASE ** (attempt + 1)
                        logger.warning("eodhd_rate_limit_retry", endpoint=endpoint, wait_s=wait)
                        await asyncio.sleep(wait)
                        continue
                    raise EODHDRateLimitError()
                if response.status_code in (401, 403):
                    raise EODHDAuthError(response.status_code)
                if response.status_code == 404:
                    raise EODHDNotFoundError(endpoint)
                if response.status_code >= 500 and attempt < self.MAX_RETRIES - 1:
                    wait = self.RETRY_BACKOFF_BASE ** (attempt + 1)
                    logger.warning("eodhd_server_error_retry", status=response.status_code, attempt=attempt)
                    await asyncio.sleep(wait)
                    continue
                raise EODHDAPIError(response.status_code, response.text[:200])

        raise EODHDAPIError(0, f"All {self.MAX_RETRIES} retries exhausted for {endpoint}")
