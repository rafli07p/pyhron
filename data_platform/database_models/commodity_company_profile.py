"""Commodity company profiles for the sensitivity linkage engine.

Replaces hardcoded company profiles (M-11 audit item) with
database-backed reference data that can be updated quarterly.
"""

import uuid
from datetime import datetime

from sqlalchemy import Float, Index, Integer, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, TIMESTAMP, UUID
from sqlalchemy.orm import Mapped, mapped_column

from shared.async_database_session import Base


class CommodityCompanyProfile(Base):
    """Company profile for commodity price sensitivity analysis.

    Stores production data, cost structure, and financial metrics
    for Indonesian commodity-linked equities (coal, CPO, nickel, energy).

    Attributes:
        id: Primary key (UUID).
        ticker: IDX ticker symbol (e.g. ``"ADRO"``, ``"AALI"``).
        commodity_type: Commodity category (``"coal"``, ``"cpo"``, ``"nickel"``, ``"energy"``).
        profile_data: JSONB with commodity-specific fields (production, costs, margins, etc.).
        shares_outstanding: Number of shares for EPS calculation.
        trailing_revenue_idr: Trailing 12-month revenue in IDR.
        net_margin: Net profit margin as a fraction.
        updated_at: Last profile update timestamp.
        created_at: Record creation timestamp.
    """

    __tablename__ = "commodity_company_profiles"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    ticker: Mapped[str] = mapped_column(String(10), nullable=False)
    commodity_type: Mapped[str] = mapped_column(String(20), nullable=False)
    profile_data: Mapped[dict[str, object]] = mapped_column(JSONB, nullable=False, default=dict)
    shares_outstanding: Mapped[int] = mapped_column(Integer, nullable=False)
    trailing_revenue_idr: Mapped[float] = mapped_column(Float, nullable=False)
    net_margin: Mapped[float] = mapped_column(Float, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), server_default="now()")
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), server_default="now()")

    __table_args__ = (
        UniqueConstraint("ticker", "commodity_type", name="uq_commodity_profile_ticker_type"),
        Index("ix_commodity_profiles_type", "commodity_type"),
    )
