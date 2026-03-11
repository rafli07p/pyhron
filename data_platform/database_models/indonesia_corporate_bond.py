"""Indonesia corporate bond market data.

Stores corporate bond pricing, ratings, and yield data from KSEI, IBPA,
and rating agencies (Pefindo, Fitch Indonesia).
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


class IndonesiaCorporateBond(Base):
    """Corporate bond daily market snapshot with credit rating.

    Attributes:
        id: Primary key (UUID).
        isin: ISIN code of the bond.
        issuer_name: Name of the issuing company.
        issuer_sector: Sector classification of the issuer.
        coupon_rate: Annual coupon rate.
        maturity_date: Bond maturity date.
        outstanding_amount_idr_bn: Outstanding amount in IDR billions.
        rating_agency: Rating agency name (e.g. ``"PEFINDO"``, ``"FITCH"``).
        credit_rating: Credit rating (e.g. ``"idAAA"``, ``"idAA+"``).
        rating_date: Date of the most recent rating action.
        yield_to_maturity: Yield to maturity.
        price: Clean price.
        price_date: Date of the market snapshot.
        ingested_at: Timestamp when the data was ingested.
    """

    __tablename__ = "corporate_bonds"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    isin: Mapped[str] = mapped_column(String(12), nullable=False)
    issuer_name: Mapped[str] = mapped_column(String(300), nullable=False)
    issuer_sector: Mapped[str | None] = mapped_column(String(100))
    coupon_rate: Mapped[Decimal | None] = mapped_column(Numeric(6, 4))
    maturity_date: Mapped[date | None] = mapped_column(Date)
    outstanding_amount_idr_bn: Mapped[Decimal | None] = mapped_column(Numeric(18, 6))
    rating_agency: Mapped[str | None] = mapped_column(String(30))
    credit_rating: Mapped[str | None] = mapped_column(String(10))
    rating_date: Mapped[date | None] = mapped_column(Date)
    yield_to_maturity: Mapped[Decimal | None] = mapped_column(Numeric(8, 4))
    price: Mapped[Decimal | None] = mapped_column(Numeric(10, 4))
    price_date: Mapped[date] = mapped_column(Date, nullable=False)
    ingested_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), server_default="now()")

    __table_args__ = (
        UniqueConstraint("isin", "price_date"),
        Index(
            "ix_indonesia_corporate_bonds_isin_date",
            "isin",
            price_date.desc(),
        ),
        Index("ix_indonesia_corporate_bonds_rating", "credit_rating"),
    )
