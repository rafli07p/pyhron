"""P&L calculation engine for the Pyhron trading platform.

Provides vectorised realised and unrealised P&L computation using
numpy / pandas with mark-to-market pricing from live market data.
"""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Any

import numpy as np
import pandas as pd
import structlog
import yfinance as yf
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from sqlalchemy.future import select

from services.portfolio.positions import Position
from shared.schemas.portfolio_events import PnLUpdate

logger = structlog.get_logger(__name__)


class PnLEngine:
    """Vectorised P&L engine with mark-to-market support.

    Uses numpy and pandas for efficient computation across large
    position sets.  Market prices can be sourced from an external
    feed or fetched on demand via yfinance.

    Parameters
    ----------
    session_factory:
        SQLAlchemy async session factory for reading position data.
    """

    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory = session_factory
        self._log = logger.bind(component="PnLEngine")
        self._price_cache: dict[str, Decimal] = {}

    # -- market data ---------------------------------------------------------

    async def _fetch_market_prices(self, symbols: list[str]) -> dict[str, Decimal]:
        """Fetch latest prices from yfinance and cache them.

        Falls back to the cached price when the network request fails
        for a given symbol.
        """
        prices: dict[str, Decimal] = {}
        try:
            tickers = yf.Tickers(" ".join(symbols))
            for sym in symbols:
                try:
                    ticker = tickers.tickers.get(sym)
                    if ticker is not None:
                        info = ticker.fast_info
                        last = getattr(info, "last_price", None)
                        if last is not None:
                            prices[sym] = Decimal(str(last))
                            self._price_cache[sym] = prices[sym]
                            continue
                except Exception:
                    self._log.warning("price_fetch_failed", symbol=sym)
                # Fallback to cache
                if sym in self._price_cache:
                    prices[sym] = self._price_cache[sym]
        except Exception:
            self._log.exception("yfinance_batch_fetch_failed")
            prices = {s: self._price_cache.get(s, Decimal("0")) for s in symbols}
        return prices

    # -- helpers -------------------------------------------------------------

    async def _load_positions_df(
        self,
        tenant_id: str,
        portfolio_id: str | None = None,
    ) -> pd.DataFrame:
        """Load positions into a pandas DataFrame for vectorised math."""
        async with self._session_factory() as session:
            stmt = select(Position).where(Position.tenant_id == tenant_id)
            if portfolio_id is not None:
                stmt = stmt.where(Position.portfolio_id == portfolio_id)
            result = await session.execute(stmt)
            rows = result.scalars().all()

        if not rows:
            return pd.DataFrame(columns=[
                "symbol", "portfolio_id", "quantity", "avg_cost",
                "market_price", "realized_pnl", "currency",
            ])

        data = [
            {
                "symbol": p.symbol,
                "portfolio_id": p.portfolio_id,
                "quantity": float(p.quantity),
                "avg_cost": float(p.avg_cost),
                "market_price": float(p.market_price),
                "realized_pnl": float(p.realized_pnl),
                "currency": p.currency,
            }
            for p in rows
        ]
        return pd.DataFrame(data)

    # -- P&L calculations (vectorised) ---------------------------------------

    async def calculate_realized_pnl(
        self,
        tenant_id: str,
        portfolio_id: str | None = None,
        symbol: str | None = None,
    ) -> Decimal:
        """Sum of realised P&L across matching positions.

        Uses numpy vectorisation for efficient aggregation.
        """
        self._log.info("calculate_realized_pnl", tenant_id=tenant_id, symbol=symbol)
        df = await self._load_positions_df(tenant_id, portfolio_id)
        if df.empty:
            return Decimal("0")
        if symbol is not None:
            df = df[df["symbol"] == symbol]
        total = np.sum(df["realized_pnl"].to_numpy(dtype=np.float64))
        return Decimal(str(round(float(total), 8)))

    async def calculate_unrealized_pnl(
        self,
        tenant_id: str,
        portfolio_id: str | None = None,
        symbol: str | None = None,
        use_live_prices: bool = True,
    ) -> Decimal:
        """Compute unrealised P&L using mark-to-market pricing.

        When *use_live_prices* is True, latest prices are fetched from
        yfinance; otherwise the stored ``market_price`` is used.
        """
        self._log.info(
            "calculate_unrealized_pnl",
            tenant_id=tenant_id,
            symbol=symbol,
            live=use_live_prices,
        )
        df = await self._load_positions_df(tenant_id, portfolio_id)
        if df.empty:
            return Decimal("0")
        if symbol is not None:
            df = df[df["symbol"] == symbol]

        if use_live_prices and not df.empty:
            symbols = df["symbol"].unique().tolist()
            prices = await self._fetch_market_prices(symbols)
            df["market_price"] = df["symbol"].map(
                lambda s: float(prices.get(s, Decimal("0")))
            )

        qty = df["quantity"].to_numpy(dtype=np.float64)
        cost = df["avg_cost"].to_numpy(dtype=np.float64)
        mkt = df["market_price"].to_numpy(dtype=np.float64)
        unrealized = np.sum(qty * (mkt - cost))
        return Decimal(str(round(float(unrealized), 8)))

    async def get_daily_pnl(
        self,
        tenant_id: str,
        portfolio_id: str,
        trading_date: date | None = None,
        previous_close_prices: dict[str, Decimal] | None = None,
    ) -> Decimal:
        """Calculate daily P&L as change from previous close.

        Parameters
        ----------
        previous_close_prices:
            Dict mapping symbol -> previous trading day's closing price.
            If not provided, yfinance is used to look up previous closes.
        """
        self._log.info("get_daily_pnl", tenant_id=tenant_id, portfolio_id=portfolio_id)
        df = await self._load_positions_df(tenant_id, portfolio_id)
        if df.empty:
            return Decimal("0")

        symbols = df["symbol"].unique().tolist()

        # Current prices
        current_prices = await self._fetch_market_prices(symbols)
        df["current_price"] = df["symbol"].map(
            lambda s: float(current_prices.get(s, Decimal("0")))
        )

        # Previous close prices
        if previous_close_prices is None:
            prev_prices: dict[str, float] = {}
            for sym in symbols:
                try:
                    ticker = yf.Ticker(sym)
                    hist = ticker.history(period="2d")
                    if len(hist) >= 2:
                        prev_prices[sym] = float(hist["Close"].iloc[-2])
                    else:
                        prev_prices[sym] = float(current_prices.get(sym, Decimal("0")))
                except Exception:
                    prev_prices[sym] = float(current_prices.get(sym, Decimal("0")))
        else:
            prev_prices = {s: float(p) for s, p in previous_close_prices.items()}

        df["prev_close"] = df["symbol"].map(lambda s: prev_prices.get(s, 0.0))

        qty = df["quantity"].to_numpy(dtype=np.float64)
        curr = df["current_price"].to_numpy(dtype=np.float64)
        prev = df["prev_close"].to_numpy(dtype=np.float64)

        daily = np.sum(qty * (curr - prev))
        return Decimal(str(round(float(daily), 8)))

    async def get_portfolio_pnl(
        self,
        tenant_id: str,
        portfolio_id: str,
        use_live_prices: bool = True,
    ) -> PnLUpdate:
        """Build a full ``PnLUpdate`` event for the portfolio.

        Combines realised, unrealised, and daily P&L into a single
        event suitable for publishing to downstream consumers.
        """
        self._log.info("get_portfolio_pnl", tenant_id=tenant_id, portfolio_id=portfolio_id)

        realized = await self.calculate_realized_pnl(tenant_id, portfolio_id)
        unrealized = await self.calculate_unrealized_pnl(
            tenant_id, portfolio_id, use_live_prices=use_live_prices,
        )
        total = realized + unrealized

        df = await self._load_positions_df(tenant_id, portfolio_id)
        market_value = Decimal("0")
        if not df.empty:
            if use_live_prices:
                symbols = df["symbol"].unique().tolist()
                prices = await self._fetch_market_prices(symbols)
                df["market_price"] = df["symbol"].map(
                    lambda s: float(prices.get(s, Decimal("0")))
                )
            qty = df["quantity"].to_numpy(dtype=np.float64)
            mkt = df["market_price"].to_numpy(dtype=np.float64)
            market_value = Decimal(str(round(float(np.sum(qty * mkt)), 8)))

        return PnLUpdate(
            portfolio_id=portfolio_id,
            tenant_id=tenant_id,
            unrealized_pnl=unrealized,
            realized_pnl=realized,
            total_pnl=total,
            daily_pnl=Decimal("0"),  # requires previous close context
            market_value=market_value,
        )


__all__ = [
    "PnLEngine",
]
