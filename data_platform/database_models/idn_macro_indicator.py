"""Indonesia macroeconomic indicator time series.

Stores macro indicators from Bank Indonesia, BPS, KEMENKEU, and other
government sources (BI Rate, CPI, GDP, M2, forex reserves, IKK, etc.).
"""

import uuid
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import Date, Index, Numeric, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import TIMESTAMP, UUID
from sqlalchemy.orm import Mapped, mapped_column

from shared.async_database_session import Base


class IdnMacroIndicator(Base):
    """Macroeconomic indicator observation.

    Attributes:
        id: Primary key (UUID).
        indicator_code: Machine-readable code (e.g. ``"bi_rate"``, ``"cpi_yoy_pct"``).
        indicator_name: Human-readable indicator name.
        source: Data source (e.g. ``"BANK_INDONESIA"``, ``"BPS"``, ``"KEMENKEU"``).
        frequency: Observation frequency (``"daily"``, ``"monthly"``, ``"quarterly"``).
        value: Numeric value of the observation.
        unit: Unit of measurement (e.g. ``"percent"``, ``"idr_trillion"``).
        period: Human-readable period label (e.g. ``"2024-Q3"``, ``"2024-07"``).
        reference_date: Reference date for the observation.
        published_at: Timestamp when the data was officially published.
        ingested_at: Timestamp when the data was ingested into the platform.
        created_at: Row creation timestamp.
    """

    __tablename__ = "idn_macro_indicator"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    indicator_code: Mapped[str] = mapped_column(String(100), nullable=False)
    indicator_name: Mapped[str] = mapped_column(String(300), nullable=False)
    source: Mapped[str] = mapped_column(String(50), nullable=False)
    frequency: Mapped[str] = mapped_column(String(30), nullable=False)
    value: Mapped[Decimal] = mapped_column(Numeric(18, 6), nullable=False)
    unit: Mapped[str] = mapped_column(String(30), nullable=False)
    period: Mapped[str] = mapped_column(String(20), nullable=False)
    reference_date: Mapped[date] = mapped_column(Date, nullable=False)
    published_at: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True), nullable=True)
    ingested_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), server_default="now()")
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), server_default="now()")

    __table_args__ = (
        UniqueConstraint("indicator_code", "reference_date", "source"),
        Index(
            "ix_indonesia_macro_indicators_code_date",
            "indicator_code",
            reference_date.desc(),
        ),
        Index("ix_indonesia_macro_indicators_source", "source"),
    )
