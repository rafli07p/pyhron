"""Exposure tracking for the Enthropy trading platform.

Calculates gross, net, sector, and currency exposures with
concentration limit checks.  All computations are vectorised
with pandas for efficient processing across large portfolios.
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any

import numpy as np
import pandas as pd
import structlog
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from sqlalchemy.future import select

from services.portfolio.positions import Position
from shared.schemas.portfolio_events import ExposureType, ExposureUpdate

logger = structlog.get_logger(__name__)


# ---------------------------------------------------------------------------
# Concentration limit configuration
# ---------------------------------------------------------------------------

class ConcentrationLimits:
    """Configurable concentration limits per tenant.

    Parameters
    ----------
    max_single_name_pct:
        Maximum portfolio weight in a single name (default 10%).
    max_sector_pct:
        Maximum portfolio weight in a single sector (default 30%).
    max_currency_pct:
        Maximum weight in a non-base currency (default 50%).
    max_gross_exposure:
        Maximum gross exposure as a multiple of NAV (default 2.0x).
    """

    def __init__(
        self,
        max_single_name_pct: float = 10.0,
        max_sector_pct: float = 30.0,
        max_currency_pct: float = 50.0,
        max_gross_exposure: float = 2.0,
    ) -> None:
        self.max_single_name_pct = max_single_name_pct
        self.max_sector_pct = max_sector_pct
        self.max_currency_pct = max_currency_pct
        self.max_gross_exposure = max_gross_exposure


# Default limits (can be overridden per tenant)
_DEFAULT_LIMITS = ConcentrationLimits()


class ExposureTracker:
    """Pandas-based exposure calculator with concentration limit checks.

    Parameters
    ----------
    session_factory:
        SQLAlchemy async session factory.
    tenant_limits:
        Optional dict mapping ``tenant_id`` -> ``ConcentrationLimits``.
        Tenants without an entry use the defaults.
    """

    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        tenant_limits: dict[str, ConcentrationLimits] | None = None,
    ) -> None:
        self._session_factory = session_factory
        self._tenant_limits = tenant_limits or {}
        self._log = logger.bind(component="ExposureTracker")

    # -- data loading --------------------------------------------------------

    async def _load_positions_df(
        self,
        tenant_id: str,
        portfolio_id: str | None = None,
    ) -> pd.DataFrame:
        async with self._session_factory() as session:
            stmt = select(Position).where(Position.tenant_id == tenant_id)
            if portfolio_id is not None:
                stmt = stmt.where(Position.portfolio_id == portfolio_id)
            result = await session.execute(stmt)
            rows = result.scalars().all()

        if not rows:
            return pd.DataFrame(columns=[
                "symbol", "portfolio_id", "quantity", "avg_cost",
                "market_price", "realized_pnl", "currency", "sector",
                "asset_class",
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
                "sector": p.sector or "Unknown",
                "asset_class": p.asset_class,
            }
            for p in rows
        ]
        df = pd.DataFrame(data)
        df["market_value"] = df["quantity"] * df["market_price"]
        df["abs_market_value"] = df["market_value"].abs()
        return df

    # -- gross / net exposure ------------------------------------------------

    async def calculate_gross_exposure(
        self,
        tenant_id: str,
        portfolio_id: str | None = None,
    ) -> Decimal:
        """Sum of absolute market values across all positions."""
        self._log.info("calculate_gross_exposure", tenant_id=tenant_id)
        df = await self._load_positions_df(tenant_id, portfolio_id)
        if df.empty:
            return Decimal("0")
        gross = float(df["abs_market_value"].sum())
        return Decimal(str(round(gross, 2)))

    async def calculate_net_exposure(
        self,
        tenant_id: str,
        portfolio_id: str | None = None,
    ) -> Decimal:
        """Sum of signed market values (long - short)."""
        self._log.info("calculate_net_exposure", tenant_id=tenant_id)
        df = await self._load_positions_df(tenant_id, portfolio_id)
        if df.empty:
            return Decimal("0")
        net = float(df["market_value"].sum())
        return Decimal(str(round(net, 2)))

    # -- sector exposure -----------------------------------------------------

    async def get_sector_exposure(
        self,
        tenant_id: str,
        portfolio_id: str | None = None,
    ) -> pd.DataFrame:
        """Return a DataFrame with sector-level exposure breakdown.

        Columns: sector, long_exposure, short_exposure, net_exposure,
        gross_exposure, weight_pct.
        """
        self._log.info("get_sector_exposure", tenant_id=tenant_id)
        df = await self._load_positions_df(tenant_id, portfolio_id)
        if df.empty:
            return pd.DataFrame(columns=[
                "sector", "long_exposure", "short_exposure",
                "net_exposure", "gross_exposure", "weight_pct",
            ])

        total_gross = df["abs_market_value"].sum()

        sector_df = df.groupby("sector").agg(
            long_exposure=("market_value", lambda x: x[x > 0].sum()),
            short_exposure=("market_value", lambda x: x[x < 0].sum()),
            net_exposure=("market_value", "sum"),
            gross_exposure=("abs_market_value", "sum"),
        ).reset_index()

        sector_df["weight_pct"] = (
            sector_df["gross_exposure"] / total_gross * 100 if total_gross > 0 else 0.0
        )
        return sector_df

    # -- currency exposure ---------------------------------------------------

    async def get_currency_exposure(
        self,
        tenant_id: str,
        portfolio_id: str | None = None,
    ) -> pd.DataFrame:
        """Return a DataFrame with currency-level exposure breakdown.

        Columns: currency, long_exposure, short_exposure, net_exposure,
        gross_exposure, weight_pct.
        """
        self._log.info("get_currency_exposure", tenant_id=tenant_id)
        df = await self._load_positions_df(tenant_id, portfolio_id)
        if df.empty:
            return pd.DataFrame(columns=[
                "currency", "long_exposure", "short_exposure",
                "net_exposure", "gross_exposure", "weight_pct",
            ])

        total_gross = df["abs_market_value"].sum()

        ccy_df = df.groupby("currency").agg(
            long_exposure=("market_value", lambda x: x[x > 0].sum()),
            short_exposure=("market_value", lambda x: x[x < 0].sum()),
            net_exposure=("market_value", "sum"),
            gross_exposure=("abs_market_value", "sum"),
        ).reset_index()

        ccy_df["weight_pct"] = (
            ccy_df["gross_exposure"] / total_gross * 100 if total_gross > 0 else 0.0
        )
        return ccy_df

    # -- concentration limits ------------------------------------------------

    async def check_concentration_limits(
        self,
        tenant_id: str,
        portfolio_id: str | None = None,
        nav: Decimal | None = None,
    ) -> list[dict[str, Any]]:
        """Check all concentration limits and return a list of breaches.

        Parameters
        ----------
        nav:
            Net asset value of the portfolio.  If not provided, gross
            exposure is used as a proxy.

        Returns
        -------
        list[dict]
            Each dict contains: ``limit_type``, ``entity``, ``value``,
            ``limit``, ``breach`` (bool).
        """
        self._log.info("check_concentration_limits", tenant_id=tenant_id)
        limits = self._tenant_limits.get(tenant_id, _DEFAULT_LIMITS)
        df = await self._load_positions_df(tenant_id, portfolio_id)
        breaches: list[dict[str, Any]] = []

        if df.empty:
            return breaches

        total_gross = float(df["abs_market_value"].sum())
        nav_value = float(nav) if nav is not None else total_gross

        if nav_value <= 0:
            return breaches

        # Single-name concentration
        for _, row in df.iterrows():
            weight = abs(row["market_value"]) / nav_value * 100
            if weight > limits.max_single_name_pct:
                breaches.append({
                    "limit_type": "single_name",
                    "entity": row["symbol"],
                    "value": round(weight, 2),
                    "limit": limits.max_single_name_pct,
                    "breach": True,
                })

        # Sector concentration
        sector_df = await self.get_sector_exposure(tenant_id, portfolio_id)
        for _, row in sector_df.iterrows():
            weight = row["gross_exposure"] / nav_value * 100
            if weight > limits.max_sector_pct:
                breaches.append({
                    "limit_type": "sector",
                    "entity": row["sector"],
                    "value": round(weight, 2),
                    "limit": limits.max_sector_pct,
                    "breach": True,
                })

        # Currency concentration (non-base)
        ccy_df = await self.get_currency_exposure(tenant_id, portfolio_id)
        for _, row in ccy_df.iterrows():
            if row["currency"] == "USD":
                continue
            weight = row["gross_exposure"] / nav_value * 100
            if weight > limits.max_currency_pct:
                breaches.append({
                    "limit_type": "currency",
                    "entity": row["currency"],
                    "value": round(weight, 2),
                    "limit": limits.max_currency_pct,
                    "breach": True,
                })

        # Gross exposure vs NAV
        gross_ratio = total_gross / nav_value
        if gross_ratio > limits.max_gross_exposure:
            breaches.append({
                "limit_type": "gross_exposure",
                "entity": "portfolio",
                "value": round(gross_ratio, 4),
                "limit": limits.max_gross_exposure,
                "breach": True,
            })

        if breaches:
            self._log.warning(
                "concentration_breaches_detected",
                tenant_id=tenant_id,
                num_breaches=len(breaches),
            )

        return breaches


__all__ = [
    "ConcentrationLimits",
    "ExposureTracker",
]
