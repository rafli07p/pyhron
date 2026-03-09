"""Indonesia fire hotspot events from NASA FIRMS.

Stores satellite-detected fire hotspot observations with geolocation,
radiative power, and optional concession mapping for ESG screening.
"""

from __future__ import annotations

import uuid
from datetime import date, datetime

from sqlalchemy import Date, Float, Index, String
from sqlalchemy.dialects.postgresql import TIMESTAMP, UUID
from sqlalchemy.orm import Mapped, mapped_column

from shared.async_database_session import Base


class IndonesiaFireHotspotEvent(Base):
    """Satellite-detected fire hotspot observation.

    Attributes:
        id: Primary key (UUID).
        latitude: Latitude of the hotspot (WGS84).
        longitude: Longitude of the hotspot (WGS84).
        brightness: Brightness temperature (Kelvin).
        fire_radiative_power: Fire radiative power (MW).
        confidence: Detection confidence level (``"nominal"``, ``"high"``).
        satellite: Satellite identifier (e.g. ``"VIIRS"``, ``"MODIS"``).
        acquisition_date: Date of satellite acquisition.
        acquisition_time: Time of acquisition (HH:MM format).
        province: Indonesian province name.
        district: District (kabupaten/kota) name.
        company_concession: Concession holder name, if mapped.
        ingested_at: Timestamp when the data was ingested.
    """

    __tablename__ = "indonesia_fire_hotspot_events"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    latitude: Mapped[float] = mapped_column(Float, nullable=False)
    longitude: Mapped[float] = mapped_column(Float, nullable=False)
    brightness: Mapped[float | None] = mapped_column(Float, nullable=True)
    fire_radiative_power: Mapped[float | None] = mapped_column(Float, nullable=True)
    confidence: Mapped[str | None] = mapped_column(String(10), nullable=True)
    satellite: Mapped[str | None] = mapped_column(String(20), nullable=True)
    acquisition_date: Mapped[date] = mapped_column(Date, nullable=False)
    acquisition_time: Mapped[str | None] = mapped_column(String(10), nullable=True)
    province: Mapped[str | None] = mapped_column(String(100), nullable=True)
    district: Mapped[str | None] = mapped_column(String(100), nullable=True)
    company_concession: Mapped[str | None] = mapped_column(String(200), nullable=True)
    ingested_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default="now()"
    )

    __table_args__ = (
        Index(
            "ix_indonesia_fire_hotspot_events_date",
            acquisition_date.desc(),
        ),
        Index(
            "ix_indonesia_fire_hotspot_events_province",
            "province",
            acquisition_date.desc(),
        ),
    )
