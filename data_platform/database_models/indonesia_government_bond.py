"""Indonesia government bond (SBN) market data.

Stores yield curve data, pricing, and duration analytics for Indonesian
sovereign bonds including FR (fixed rate) and PBS (sukuk) series.
"""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

from sqlalchemy import Date, Index, Numeric, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import TIMESTAMP, UUID
from sqlalchemy.orm import Mapped, mapped_column

from shared.async_database_session import Base

if TYPE_CHECKING:
    from datetime import date, datetime
    from decimal import Decimal


class IndonesiaGovernmentBond(Base):
    """Government bond (SBN) daily market snapshot.

    Attributes:
        id: Primary key (UUID).
        series_code: Bond series code (e.g. ``"FR0091"``, ``"PBS001"``).
        instrument_type: Instrument type (e.g. ``"FR"``, ``"PBS"``, ``"SPN"``).
        coupon_rate: Annual coupon rate.
        maturity_date: Bond maturity date.
        outstanding_amount_idr_bn: Outstanding amount in IDR billions.
        bid_yield: Best bid yield.
        ask_yield: Best ask yield.
        mid_yield: Mid yield.
        bid_price: Best bid price.
        ask_price: Best ask price.
        duration: Macaulay duration.
        modified_duration: Modified duration.
        convexity: Convexity.
        daily_volume_idr_bn: Daily trading volume in IDR billions.
        price_date: Date of the market snapshot.
        ingested_at: Timestamp when the data was ingested.
    """

    __tablename__ = "government_bonds"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    series_code: Mapped[str] = mapped_column(String(30), nullable=False)
    instrument_type: Mapped[str] = mapped_column(String(30), nullable=False)
    coupon_rate: Mapped[Decimal | None] = mapped_column(Numeric(6, 4))
    maturity_date: Mapped[date | None] = mapped_column(Date)
    outstanding_amount_idr_bn: Mapped[Decimal | None] = mapped_column(Numeric(18, 6))
    bid_yield: Mapped[Decimal | None] = mapped_column(Numeric(8, 4))
    ask_yield: Mapped[Decimal | None] = mapped_column(Numeric(8, 4))
    mid_yield: Mapped[Decimal | None] = mapped_column(Numeric(8, 4))
    bid_price: Mapped[Decimal | None] = mapped_column(Numeric(10, 4))
    ask_price: Mapped[Decimal | None] = mapped_column(Numeric(10, 4))
    duration: Mapped[Decimal | None] = mapped_column(Numeric(8, 4))
    modified_duration: Mapped[Decimal | None] = mapped_column(Numeric(8, 4))
    convexity: Mapped[Decimal | None] = mapped_column(Numeric(10, 4))
    daily_volume_idr_bn: Mapped[Decimal | None] = mapped_column(Numeric(18, 6))
    price_date: Mapped[date] = mapped_column(Date, nullable=False)
    ingested_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), server_default="now()")

    __table_args__ = (
        UniqueConstraint("series_code", "price_date"),
        Index(
            "ix_indonesia_government_bonds_series_date",
            "series_code",
            price_date.desc(),
        ),
        Index("ix_indonesia_government_bonds_type", "instrument_type"),
    )
