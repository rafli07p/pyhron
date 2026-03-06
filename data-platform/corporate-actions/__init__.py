"""
Corporate actions engine for the Enthropy data platform.

Fetches and stores dividends, splits, and mergers from the Polygon.io
API (with yfinance fallback).  Adjusts historical prices for splits
and dividends.
"""

from __future__ import annotations

from datetime import date, datetime, timezone
from decimal import Decimal
from typing import Optional, Sequence

import structlog
from polygon import RESTClient as PolygonClient
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

logger = structlog.get_logger(__name__)


# ---------------------------------------------------------------------------
# Re-use the historical-storage ORM models
# ---------------------------------------------------------------------------
import importlib
import sys
from pathlib import Path as _Path

def _import_historical_storage():
    """Import the historical-storage sub-package (hyphenated directory)."""
    _pkg_dir = _Path(__file__).resolve().parent.parent
    _hs_init = _pkg_dir / "historical-storage" / "__init__.py"
    _mod_name = "data_platform.historical_storage"
    if _mod_name in sys.modules:
        return sys.modules[_mod_name]
    spec = importlib.util.spec_from_file_location(_mod_name, str(_hs_init))
    mod = importlib.util.module_from_spec(spec)
    sys.modules[_mod_name] = mod
    spec.loader.exec_module(mod)
    return mod

_hs = _import_historical_storage()
Base = _hs.Base
CorporateAction = _hs.CorporateAction
OHLCVRecord = _hs.OHLCVRecord


# ---------------------------------------------------------------------------
# CorporateActionsEngine
# ---------------------------------------------------------------------------

class CorporateActionsEngine:
    """Fetch, store, and apply corporate actions from Polygon.io.

    Parameters
    ----------
    polygon_api_key : str
        Polygon.io API key.
    database_url : str
        Async SQLAlchemy connection string for the historical store.
    tenant_id : str
        Multi-tenancy identifier.
    use_yfinance_fallback : bool
        When ``True``, falls back to ``yfinance`` if Polygon returns
        no results.
    """

    def __init__(
        self,
        polygon_api_key: str,
        database_url: str = "postgresql+asyncpg://localhost/enthropy",
        tenant_id: str = "default",
        use_yfinance_fallback: bool = True,
    ) -> None:
        self.tenant_id = tenant_id
        self._log = logger.bind(tenant_id=tenant_id, component="CorporateActionsEngine")
        self._polygon = PolygonClient(api_key=polygon_api_key)
        self._use_yfinance = use_yfinance_fallback

        self._engine = create_async_engine(
            database_url, pool_size=5, max_overflow=10, pool_pre_ping=True,
        )
        self._session_factory = async_sessionmaker(self._engine, expire_on_commit=False)
        self._log.info("corporate_actions_engine_initialised")

    async def close(self) -> None:
        await self._engine.dispose()

    # ------------------------------------------------------------------
    # Sync from Polygon
    # ------------------------------------------------------------------

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, max=30),
        retry=retry_if_exception_type((OSError, ConnectionError, TimeoutError)),
        reraise=True,
    )
    async def sync_corporate_actions(
        self,
        symbol: str,
        *,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
    ) -> dict[str, int]:
        """Fetch dividends and splits from Polygon and persist them.

        Returns a dict ``{"dividends": N, "splits": M}`` with counts.
        """
        import asyncio

        start_str = start_date.isoformat() if start_date else None
        end_str = end_date.isoformat() if end_date else None

        dividends_count = 0
        splits_count = 0

        # --- Dividends -------------------------------------------------------
        try:
            divs = await asyncio.to_thread(
                self._fetch_polygon_dividends, symbol, start_str, end_str
            )
            dividends_count = await self._store_dividends(symbol, divs)
        except Exception as exc:
            self._log.warning("polygon_dividends_failed", symbol=symbol, error=str(exc))
            if self._use_yfinance:
                dividends_count = await self._sync_dividends_yfinance(symbol, start_date, end_date)

        # --- Splits -----------------------------------------------------------
        try:
            splits = await asyncio.to_thread(
                self._fetch_polygon_splits, symbol, start_str, end_str
            )
            splits_count = await self._store_splits(symbol, splits)
        except Exception as exc:
            self._log.warning("polygon_splits_failed", symbol=symbol, error=str(exc))
            if self._use_yfinance:
                splits_count = await self._sync_splits_yfinance(symbol, start_date, end_date)

        self._log.info(
            "corporate_actions_synced",
            symbol=symbol,
            dividends=dividends_count,
            splits=splits_count,
        )
        return {"dividends": dividends_count, "splits": splits_count}

    # ------------------------------------------------------------------
    # Polygon fetchers (run in thread)
    # ------------------------------------------------------------------

    def _fetch_polygon_dividends(
        self, symbol: str, start: Optional[str], end: Optional[str]
    ) -> list[dict]:
        results = []
        params: dict = {"ticker": symbol.upper()}
        if start:
            params["ex_dividend_date.gte"] = start
        if end:
            params["ex_dividend_date.lte"] = end

        for div in self._polygon.list_dividends(**params):
            results.append({
                "symbol": div.ticker,
                "ex_date": div.ex_dividend_date,
                "record_date": getattr(div, "record_date", None),
                "payment_date": getattr(div, "pay_date", None),
                "amount": float(div.cash_amount) if div.cash_amount else None,
                "currency": getattr(div, "currency", "USD") or "USD",
                "frequency": getattr(div, "frequency", None),
                "description": getattr(div, "description", None),
            })
        return results

    def _fetch_polygon_splits(
        self, symbol: str, start: Optional[str], end: Optional[str]
    ) -> list[dict]:
        results = []
        params: dict = {"ticker": symbol.upper()}
        if start:
            params["execution_date.gte"] = start
        if end:
            params["execution_date.lte"] = end

        for split in self._polygon.list_splits(**params):
            ratio = None
            if split.split_to and split.split_from:
                ratio = float(split.split_to) / float(split.split_from)
            results.append({
                "symbol": split.ticker,
                "ex_date": split.execution_date,
                "ratio": ratio,
                "split_from": getattr(split, "split_from", None),
                "split_to": getattr(split, "split_to", None),
            })
        return results

    # ------------------------------------------------------------------
    # yfinance fallback
    # ------------------------------------------------------------------

    async def _sync_dividends_yfinance(
        self, symbol: str, start: Optional[date], end: Optional[date]
    ) -> int:
        import asyncio

        try:
            import yfinance as yf
        except ImportError:
            self._log.error("yfinance_not_installed")
            return 0

        def _fetch() -> list[dict]:
            ticker = yf.Ticker(symbol)
            divs = ticker.dividends
            if divs.empty:
                return []
            records = []
            for ts, amount in divs.items():
                ex = ts.date() if hasattr(ts, "date") else ts
                if start and ex < start:
                    continue
                if end and ex > end:
                    continue
                records.append({
                    "symbol": symbol.upper(),
                    "ex_date": ex.isoformat() if isinstance(ex, date) else str(ex),
                    "amount": float(amount),
                    "currency": "USD",
                })
            return records

        divs = await asyncio.to_thread(_fetch)
        return await self._store_dividends(symbol, divs)

    async def _sync_splits_yfinance(
        self, symbol: str, start: Optional[date], end: Optional[date]
    ) -> int:
        import asyncio

        try:
            import yfinance as yf
        except ImportError:
            self._log.error("yfinance_not_installed")
            return 0

        def _fetch() -> list[dict]:
            ticker = yf.Ticker(symbol)
            splits = ticker.splits
            if splits.empty:
                return []
            records = []
            for ts, ratio in splits.items():
                ex = ts.date() if hasattr(ts, "date") else ts
                if start and ex < start:
                    continue
                if end and ex > end:
                    continue
                records.append({
                    "symbol": symbol.upper(),
                    "ex_date": ex.isoformat() if isinstance(ex, date) else str(ex),
                    "ratio": float(ratio),
                })
            return records

        splits = await asyncio.to_thread(_fetch)
        return await self._store_splits(symbol, splits)

    # ------------------------------------------------------------------
    # Persist helpers
    # ------------------------------------------------------------------

    async def _store_dividends(self, symbol: str, divs: list[dict]) -> int:
        if not divs:
            return 0
        async with self._session_factory() as session:
            async with session.begin():
                count = 0
                for d in divs:
                    ex = d.get("ex_date")
                    if isinstance(ex, str):
                        ex = date.fromisoformat(ex)
                    record_date = d.get("record_date")
                    if isinstance(record_date, str):
                        record_date = date.fromisoformat(record_date)
                    payment_date = d.get("payment_date")
                    if isinstance(payment_date, str):
                        payment_date = date.fromisoformat(payment_date)

                    # Skip duplicates
                    existing = (
                        await session.execute(
                            select(CorporateAction).where(
                                CorporateAction.tenant_id == self.tenant_id,
                                CorporateAction.symbol == symbol.upper(),
                                CorporateAction.action_type == "dividend",
                                CorporateAction.ex_date == ex,
                            )
                        )
                    ).scalar_one_or_none()
                    if existing:
                        continue

                    record = CorporateAction(
                        tenant_id=self.tenant_id,
                        symbol=symbol.upper(),
                        action_type="dividend",
                        ex_date=ex,
                        record_date=record_date,
                        payment_date=payment_date,
                        amount=Decimal(str(d["amount"])) if d.get("amount") else None,
                        currency=d.get("currency", "USD"),
                        description=d.get("description"),
                        source="polygon",
                    )
                    session.add(record)
                    count += 1
        self._log.info("dividends_stored", symbol=symbol, count=count)
        return count

    async def _store_splits(self, symbol: str, splits: list[dict]) -> int:
        if not splits:
            return 0
        async with self._session_factory() as session:
            async with session.begin():
                count = 0
                for s in splits:
                    ex = s.get("ex_date")
                    if isinstance(ex, str):
                        ex = date.fromisoformat(ex)

                    existing = (
                        await session.execute(
                            select(CorporateAction).where(
                                CorporateAction.tenant_id == self.tenant_id,
                                CorporateAction.symbol == symbol.upper(),
                                CorporateAction.action_type == "split",
                                CorporateAction.ex_date == ex,
                            )
                        )
                    ).scalar_one_or_none()
                    if existing:
                        continue

                    record = CorporateAction(
                        tenant_id=self.tenant_id,
                        symbol=symbol.upper(),
                        action_type="split",
                        ex_date=ex,
                        ratio=Decimal(str(s["ratio"])) if s.get("ratio") else None,
                        source="polygon",
                    )
                    session.add(record)
                    count += 1
        self._log.info("splits_stored", symbol=symbol, count=count)
        return count

    # ------------------------------------------------------------------
    # Adjust historical prices
    # ------------------------------------------------------------------

    async def adjust_prices(
        self,
        symbol: str,
        *,
        adjust_dividends: bool = True,
        adjust_splits: bool = True,
    ) -> int:
        """Retroactively adjust OHLCV records for splits and dividends.

        Applies a cumulative adjustment factor walking backwards from
        the most recent bar.  Returns the number of bars updated.
        """
        # Fetch all actions ordered by ex_date DESC
        async with self._session_factory() as session:
            actions_stmt = (
                select(CorporateAction)
                .where(CorporateAction.tenant_id == self.tenant_id)
                .where(CorporateAction.symbol == symbol.upper())
                .order_by(CorporateAction.ex_date.desc())
            )
            actions = (await session.execute(actions_stmt)).scalars().all()

        if not actions:
            self._log.info("no_actions_to_adjust", symbol=symbol)
            return 0

        # Build adjustment factors keyed by date
        adjustments: list[tuple[date, Decimal]] = []
        for action in actions:
            if action.action_type == "split" and adjust_splits and action.ratio:
                adjustments.append((action.ex_date, action.ratio))
            elif action.action_type == "dividend" and adjust_dividends and action.amount:
                # We'll adjust once we know the closing price
                adjustments.append((action.ex_date, action.amount * Decimal("-1")))

        if not adjustments:
            return 0

        updated = 0
        async with self._session_factory() as session:
            async with session.begin():
                # Fetch all bars for the symbol
                bars_stmt = (
                    select(OHLCVRecord)
                    .where(OHLCVRecord.tenant_id == self.tenant_id)
                    .where(OHLCVRecord.symbol == symbol.upper())
                    .order_by(OHLCVRecord.bar_date.asc())
                )
                bars = (await session.execute(bars_stmt)).scalars().all()

                for bar in bars:
                    cumulative_factor = Decimal("1")
                    dividend_adj = Decimal("0")

                    for ex_date, factor in adjustments:
                        if bar.bar_date < ex_date:
                            if factor < 0:
                                # Dividend adjustment (negative amount stored)
                                dividend_adj += abs(factor)
                            else:
                                # Split ratio
                                cumulative_factor *= factor

                    if cumulative_factor != Decimal("1") or dividend_adj > 0:
                        if cumulative_factor != Decimal("1"):
                            bar.open = bar.open / cumulative_factor
                            bar.high = bar.high / cumulative_factor
                            bar.low = bar.low / cumulative_factor
                            bar.close = bar.close / cumulative_factor
                            bar.volume = int(bar.volume * cumulative_factor)
                        if dividend_adj > 0 and bar.close > 0:
                            adj_factor = (bar.close - dividend_adj) / bar.close
                            bar.open = bar.open * adj_factor
                            bar.high = bar.high * adj_factor
                            bar.low = bar.low * adj_factor
                            bar.close = bar.close * adj_factor
                        updated += 1

        self._log.info("prices_adjusted", symbol=symbol, bars_updated=updated)
        return updated

    # ------------------------------------------------------------------
    # Query
    # ------------------------------------------------------------------

    async def get_actions_for_symbol(
        self,
        symbol: str,
        *,
        action_type: Optional[str] = None,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
    ) -> list[dict]:
        """Return corporate actions for *symbol*."""
        stmt = (
            select(CorporateAction)
            .where(CorporateAction.tenant_id == self.tenant_id)
            .where(CorporateAction.symbol == symbol.upper())
        )
        if action_type:
            stmt = stmt.where(CorporateAction.action_type == action_type)
        if start_date:
            stmt = stmt.where(CorporateAction.ex_date >= start_date)
        if end_date:
            stmt = stmt.where(CorporateAction.ex_date <= end_date)
        stmt = stmt.order_by(CorporateAction.ex_date.desc())

        async with self._session_factory() as session:
            result = await session.execute(stmt)
            rows = result.scalars().all()

        return [
            {
                "symbol": r.symbol,
                "action_type": r.action_type,
                "ex_date": r.ex_date.isoformat(),
                "record_date": r.record_date.isoformat() if r.record_date else None,
                "payment_date": r.payment_date.isoformat() if r.payment_date else None,
                "ratio": float(r.ratio) if r.ratio else None,
                "amount": float(r.amount) if r.amount else None,
                "currency": r.currency,
                "description": r.description,
                "source": r.source,
            }
            for r in rows
        ]


__all__ = [
    "CorporateActionsEngine",
]
