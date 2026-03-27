"""Position management for the Pyhron trading platform.

Tracks open positions per tenant with SQLAlchemy persistence and
real-time updates driven by OrderFill events.
"""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from uuid import uuid4

import structlog
from sqlalchemy import DateTime, Index, Numeric, String, Text
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from sqlalchemy.future import select
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from shared.schemas.order_events import OrderFill, OrderSide
from shared.schemas.portfolio_events import AssetClass, PositionUpdate

logger = structlog.get_logger(__name__)


# SQLAlchemy model

class Base(DeclarativeBase):
    """Declarative base for portfolio models."""


class Position(Base):
    """Persistent position record.

    Each row represents a tenant's current position in a single symbol.
    The composite unique constraint (tenant_id, portfolio_id, symbol)
    ensures exactly one row per holding per book per tenant.
    """

    __tablename__ = "positions"
    __table_args__ = (
        Index("ix_positions_tenant_portfolio", "tenant_id", "portfolio_id"),
        Index("ix_positions_tenant_symbol", "tenant_id", "symbol"),
    )

    id: Mapped[str] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    tenant_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    portfolio_id: Mapped[str] = mapped_column(String(64), nullable=False)
    symbol: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    quantity: Mapped[Decimal] = mapped_column(Numeric(20, 8), nullable=False, default=0)
    avg_cost: Mapped[Decimal] = mapped_column(Numeric(20, 8), nullable=False, default=0)
    realized_pnl: Mapped[Decimal] = mapped_column(Numeric(20, 8), nullable=False, default=0)
    market_price: Mapped[Decimal] = mapped_column(Numeric(20, 8), nullable=False, default=0)
    asset_class: Mapped[str] = mapped_column(String(32), nullable=False, default=AssetClass.EQUITY.value)
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="USD")
    sector: Mapped[str | None] = mapped_column(String(64), nullable=True)
    last_fill_id: Mapped[str | None] = mapped_column(Text, nullable=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC), onupdate=lambda: datetime.now(UTC))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC))


# Position manager

class PositionManager:
    """Manages positions with real-time updates from order fills.

    Parameters
    ----------
    session_factory:
        SQLAlchemy async session factory bound to a tenant-aware engine.
    """

    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory = session_factory
        self._log = logger.bind(component="PositionManager")

    # public API

    async def track_position(
        self,
        tenant_id: str,
        portfolio_id: str,
        symbol: str,
        quantity: Decimal,
        avg_cost: Decimal,
        *,
        asset_class: AssetClass = AssetClass.EQUITY,
        currency: str = "USD",
        sector: str | None = None,
    ) -> Position:
        """Create or replace a position record manually.

        Typically used for initial portfolio loading or reconciliation.
        """
        self._log.info(
            "track_position",
            tenant_id=tenant_id,
            portfolio_id=portfolio_id,
            symbol=symbol,
            quantity=str(quantity),
        )
        async with self._session_factory() as session:
            pos = await self._get_or_create(session, tenant_id, portfolio_id, symbol)
            pos.quantity = quantity
            pos.avg_cost = avg_cost
            pos.asset_class = asset_class.value
            pos.currency = currency
            pos.sector = sector
            pos.updated_at = datetime.now(UTC)
            session.add(pos)
            await session.commit()
            await session.refresh(pos)
            return pos

    async def get_positions(
        self,
        tenant_id: str,
        portfolio_id: str | None = None,
        symbol: str | None = None,
    ) -> list[Position]:
        """Return positions for a tenant, optionally filtered by portfolio/symbol."""
        async with self._session_factory() as session:
            stmt = select(Position).where(Position.tenant_id == tenant_id)
            if portfolio_id is not None:
                stmt = stmt.where(Position.portfolio_id == portfolio_id)
            if symbol is not None:
                stmt = stmt.where(Position.symbol == symbol)
            result = await session.execute(stmt)
            return list(result.scalars().all())

    async def update_on_fill(
        self,
        fill: OrderFill,
        portfolio_id: str = "default",
    ) -> Position:
        """Update position state in response to an OrderFill event.

        Applies FIFO cost-basis accounting: when a fill reduces an
        existing position (or flips it), realised P&L is booked.

        Parameters
        ----------
        fill:
            The fill event from the OMS.
        portfolio_id:
            Target portfolio/book for this position.

        Returns
        -------
        Position
            The updated position row.
        """
        self._log.info(
            "update_on_fill",
            tenant_id=fill.tenant_id,
            symbol=fill.symbol,
            side=fill.side,
            fill_qty=str(fill.fill_qty),
            fill_price=str(fill.fill_price),
        )

        async with self._session_factory() as session:
            pos = await self._get_or_create(session, fill.tenant_id, portfolio_id, fill.symbol)

            signed_qty = fill.fill_qty if fill.side == OrderSide.BUY else -fill.fill_qty
            old_qty = pos.quantity
            new_qty = old_qty + signed_qty

            # Realised P&L: when reducing or flipping a position
            if old_qty != Decimal("0") and (
                (old_qty > 0 and signed_qty < 0) or (old_qty < 0 and signed_qty > 0)
            ):
                closed_qty = min(abs(signed_qty), abs(old_qty))
                pnl_per_unit = fill.fill_price - pos.avg_cost
                if old_qty < 0:
                    pnl_per_unit = -pnl_per_unit
                pos.realized_pnl += pnl_per_unit * closed_qty

            # Update average cost when adding to position
            if new_qty != Decimal("0"):
                if (old_qty >= 0 and signed_qty > 0) or (old_qty <= 0 and signed_qty < 0):
                    # Adding in the same direction
                    total_cost = abs(old_qty) * pos.avg_cost + abs(signed_qty) * fill.fill_price
                    pos.avg_cost = total_cost / abs(new_qty)
                elif abs(new_qty) > abs(old_qty):
                    # Position flipped: new cost is fill price
                    pos.avg_cost = fill.fill_price
            else:
                pos.avg_cost = Decimal("0")

            pos.quantity = new_qty
            pos.market_price = fill.fill_price
            pos.last_fill_id = str(fill.fill_id)
            pos.updated_at = datetime.now(UTC)

            session.add(pos)
            await session.commit()
            await session.refresh(pos)
            return pos

    async def get_position_value(
        self,
        tenant_id: str,
        portfolio_id: str,
        symbol: str,
        current_price: Decimal | None = None,
    ) -> Decimal:
        """Return the market value of a single position.

        If *current_price* is provided it overrides the stored
        ``market_price``.
        """
        positions = await self.get_positions(tenant_id, portfolio_id, symbol)
        if not positions:
            return Decimal("0")
        pos = positions[0]
        price = current_price if current_price is not None else pos.market_price
        return pos.quantity * price

    # helpers

    async def _get_or_create(
        self,
        session: AsyncSession,
        tenant_id: str,
        portfolio_id: str,
        symbol: str,
    ) -> Position:
        stmt = (
            select(Position)
            .where(Position.tenant_id == tenant_id)
            .where(Position.portfolio_id == portfolio_id)
            .where(Position.symbol == symbol)
        )
        result = await session.execute(stmt)
        pos = result.scalar_one_or_none()
        if pos is None:
            pos = Position(
                id=uuid4(),
                tenant_id=tenant_id,
                portfolio_id=portfolio_id,
                symbol=symbol,
                quantity=Decimal("0"),
                avg_cost=Decimal("0"),
                realized_pnl=Decimal("0"),
                market_price=Decimal("0"),
                created_at=datetime.now(UTC),
                updated_at=datetime.now(UTC),
            )
        return pos

    async def emit_position_update(self, pos: Position) -> PositionUpdate:
        """Build a ``PositionUpdate`` event from the current DB state."""
        unrealized = (pos.market_price - pos.avg_cost) * pos.quantity
        return PositionUpdate(
            portfolio_id=pos.portfolio_id,
            tenant_id=pos.tenant_id,
            symbol=pos.symbol,
            quantity=pos.quantity,
            avg_cost=pos.avg_cost,
            market_price=pos.market_price,
            market_value=pos.quantity * pos.market_price,
            unrealized_pnl=unrealized,
            realized_pnl=pos.realized_pnl,
            asset_class=AssetClass(pos.asset_class),
            currency=pos.currency,
        )


__all__ = [
    "Base",
    "Position",
    "PositionManager",
]
