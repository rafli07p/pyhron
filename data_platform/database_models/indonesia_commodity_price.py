"""Indonesia-relevant commodity daily prices.

Tracks daily prices for commodities critical to Indonesian markets:
CPO (palm oil), HBA coal, LME nickel, ICP crude oil, and others.
"""

from __future__ import annotations

import uuid
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import Date, Index, Numeric, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import TIMESTAMP, UUID
from sqlalchemy.orm import Mapped, mapped_column

from shared.async_database_session import Base


class IndonesiaCommodityPrice(Base):
    """Daily commodity price observation.

    Attributes:
        id: Primary key (UUID).
        commodity_code: Machine-readable code (e.g. ``"CPO"``, ``"HBA_COAL"``).
        commodity_name: Human-readable commodity name.
        price: Price value.
        currency: Price currency ISO code (e.g. ``"USD"``, ``"IDR"``).
        unit: Price unit (e.g. ``"per_ton"``, ``"per_barrel"``).
        source: Data source identifier.
        price_date: Date of the price observation.
        ingested_at: Timestamp when the data was ingested.
    """

    __tablename__ = "indonesia_commodity_prices"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    commodity_code: Mapped[str] = mapped_column(String(30), nullable=False)
    commodity_name: Mapped[str] = mapped_column(String(200), nullable=False)
    price: Mapped[Decimal] = mapped_column(Numeric(18, 6), nullable=False)
    currency: Mapped[str] = mapped_column(String(10), nullable=False)
    unit: Mapped[str] = mapped_column(String(30), nullable=False)
    source: Mapped[str] = mapped_column(String(50), nullable=False)
    price_date: Mapped[date] = mapped_column(Date, nullable=False)
    ingested_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default="now()"
    )

    __table_args__ = (
        UniqueConstraint("commodity_code", "price_date", "source"),
        Index(
            "ix_indonesia_commodity_prices_code_date",
            "commodity_code",
            price_date.desc(),
        ),
    )
