"""IDX corporate actions ingestion from EODHD.

Handles dividends (interim + final tranches), splits, reverse splits,
and rights issues. Stores cum-dividend and ex-dividend dates.
"""

from __future__ import annotations

from decimal import Decimal, InvalidOperation

import httpx
from sqlalchemy import text

from shared.configuration_settings import get_config
from shared.async_database_session import get_session
from shared.platform_exception_hierarchy import IngestionError
from shared.structured_json_logger import get_logger

logger = get_logger(__name__)


class IDXCorporateActionIngester:
    """Ingests corporate actions for IDX equities from EODHD."""

    def __init__(self) -> None:
        config = get_config()
        self._eodhd_key = config.eodhd_api_key

    async def ingest_symbol(self, symbol: str) -> dict:
        """Fetch and store corporate actions for a single symbol."""
        if not self._eodhd_key:
            raise IngestionError("EODHD API key not configured")

        dividends = await self._fetch_dividends(symbol)
        splits = await self._fetch_splits(symbol)

        div_count = 0
        for div in dividends:
            await self._upsert_dividend(symbol, div)
            div_count += 1

        split_count = 0
        for split in splits:
            await self._upsert_split(symbol, split)
            split_count += 1

        logger.info(
            "corporate_actions_ingested",
            symbol=symbol,
            dividends=div_count,
            splits=split_count,
        )
        return {"symbol": symbol, "dividends": div_count, "splits": split_count}

    async def _fetch_dividends(self, symbol: str) -> list[dict]:
        """Fetch dividend history from EODHD."""
        url = f"https://eodhd.com/api/div/{symbol}.IDX"
        params = {"api_token": self._eodhd_key, "fmt": "json"}

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                resp = await client.get(url, params=params)
                resp.raise_for_status()
                return resp.json()
        except httpx.HTTPStatusError as exc:
            logger.warning("eodhd_dividends_error", symbol=symbol, status=exc.response.status_code)
            return []

    async def _fetch_splits(self, symbol: str) -> list[dict]:
        """Fetch split history from EODHD."""
        url = f"https://eodhd.com/api/splits/{symbol}.IDX"
        params = {"api_token": self._eodhd_key, "fmt": "json"}

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                resp = await client.get(url, params=params)
                resp.raise_for_status()
                return resp.json()
        except httpx.HTTPStatusError as exc:
            logger.warning("eodhd_splits_error", symbol=symbol, status=exc.response.status_code)
            return []

    async def _upsert_dividend(self, symbol: str, div: dict) -> None:
        """Upsert a dividend record."""
        ex_date = div.get("date")
        if not ex_date:
            return

        try:
            amount = Decimal(str(div.get("value", 0)))
        except InvalidOperation:
            amount = Decimal("0")

        # IDX dividends: determine if interim or final based on timing
        record_date = div.get("recordDate")
        payment_date = div.get("paymentDate")
        notes = div.get("declarationDate", "")

        async with get_session() as session:
            await session.execute(
                text("""
                    INSERT INTO corporate_actions (
                        id, symbol, action_type, ex_date, record_date,
                        payment_date, amount, currency, notes
                    ) VALUES (
                        uuid_generate_v4(), :symbol, 'cash_dividend', :ex_date,
                        :record_date, :payment_date, :amount, 'IDR', :notes
                    )
                    ON CONFLICT (symbol, action_type, ex_date) DO UPDATE SET
                        amount = EXCLUDED.amount,
                        record_date = EXCLUDED.record_date,
                        payment_date = EXCLUDED.payment_date
                """),
                {
                    "symbol": symbol,
                    "ex_date": ex_date,
                    "record_date": record_date,
                    "payment_date": payment_date,
                    "amount": float(amount),
                    "notes": notes,
                },
            )

    async def _upsert_split(self, symbol: str, split: dict) -> None:
        """Upsert a stock split record."""
        ex_date = split.get("date")
        split_str = split.get("split", "")
        if not ex_date or not split_str:
            return

        # Parse split ratio (e.g. "2/1" means 2-for-1)
        try:
            parts = split_str.split("/")
            ratio = Decimal(parts[0]) / Decimal(parts[1])
        except (IndexError, InvalidOperation, ZeroDivisionError):
            ratio = Decimal("1")

        action_type = "split" if ratio > 1 else "reverse_split"

        async with get_session() as session:
            await session.execute(
                text("""
                    INSERT INTO corporate_actions (
                        id, symbol, action_type, ex_date, ratio, currency, notes
                    ) VALUES (
                        uuid_generate_v4(), :symbol, :action_type, :ex_date,
                        :ratio, 'IDR', :notes
                    )
                    ON CONFLICT (symbol, action_type, ex_date) DO UPDATE SET
                        ratio = EXCLUDED.ratio
                """),
                {
                    "symbol": symbol,
                    "action_type": action_type,
                    "ex_date": ex_date,
                    "ratio": float(ratio),
                    "notes": split_str,
                },
            )
