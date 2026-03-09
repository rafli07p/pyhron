"""Indonesia weather rainfall observations from BMKG.

Stores daily rainfall measurements by province and weather station,
used for commodity impact analysis (agriculture, mining).
"""

from __future__ import annotations

import uuid
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import Date, Float, Index, Numeric, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import TIMESTAMP, UUID
from sqlalchemy.orm import Mapped, mapped_column

from shared.async_database_session import Base


class IndonesiaWeatherRainfall(Base):
    """Daily rainfall observation from a BMKG weather station.

    Attributes:
        id: Primary key (UUID).
        province: Indonesian province name.
        station_name: BMKG weather station name.
        latitude: Station latitude (WGS84).
        longitude: Station longitude (WGS84).
        rainfall_mm: Daily rainfall in millimetres.
        observation_date: Date of the observation.
        source: Data source identifier (e.g. ``"BMKG"``).
        ingested_at: Timestamp when the data was ingested.
    """

    __tablename__ = "indonesia_weather_rainfall"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    province: Mapped[str] = mapped_column(String(100), nullable=False)
    station_name: Mapped[str] = mapped_column(String(200), nullable=False)
    latitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    longitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    rainfall_mm: Mapped[Decimal | None] = mapped_column(Numeric(8, 2), nullable=True)
    observation_date: Mapped[date] = mapped_column(Date, nullable=False)
    source: Mapped[str] = mapped_column(String(50), nullable=False)
    ingested_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default="now()"
    )

    __table_args__ = (
        UniqueConstraint("station_name", "observation_date"),
        Index(
            "ix_indonesia_weather_rainfall_province_date",
            "province",
            observation_date.desc(),
        ),
    )
