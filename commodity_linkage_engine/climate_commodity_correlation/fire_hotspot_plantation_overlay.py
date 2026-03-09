"""NASA FIRMS fire hotspot overlay on Indonesian plantation concessions.

Fetches active fire/hotspot data from NASA FIRMS (Fire Information for
Resource Management System) and overlays it on Indonesian plantation
concession maps to assess damage risk to palm oil, pulp & paper, and
rubber plantations.

Data sources:
  - NASA FIRMS: MODIS & VIIRS active fire data.
  - KLHK (Ministry of Environment): Plantation concession boundaries.

Usage::

    overlay = FireHotspotPlantationOverlay(firms_api_key="...")
    alerts = await overlay.detect_plantation_fires(hotspots)
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

import httpx

from shared.structured_json_logger import get_logger
from shared.configuration_settings import get_config

logger = get_logger(__name__)

_FIRMS_BASE_URL = "https://firms.modaps.eosdis.nasa.gov/api/area/csv"


@dataclass(frozen=True)
class FireHotspot:
    """Single fire/hotspot detection from FIRMS satellite data.

    Attributes:
        latitude: Latitude (decimal degrees).
        longitude: Longitude (decimal degrees).
        brightness: Fire radiative brightness (Kelvin).
        confidence: Detection confidence (0-100 for MODIS, nominal/high for VIIRS).
        acquired_at: UTC datetime of satellite pass.
        satellite: Satellite source (MODIS Terra/Aqua, VIIRS SNPP/NOAA20).
        frp: Fire Radiative Power (MW).
    """

    latitude: float
    longitude: float
    brightness: float
    confidence: int
    acquired_at: datetime
    satellite: str
    frp: float


@dataclass(frozen=True)
class PlantationConcession:
    """Plantation concession boundary definition.

    Attributes:
        concession_id: Unique concession identifier.
        company_name: Operating company name.
        ticker: IDX ticker if publicly listed (None otherwise).
        commodity: Plantation commodity (palm_oil, pulp_paper, rubber).
        bbox: Bounding box (min_lat, min_lon, max_lat, max_lon).
        area_ha: Concession area in hectares.
        province: Indonesian province.
    """

    concession_id: str
    company_name: str
    ticker: str | None
    commodity: str
    bbox: tuple[float, float, float, float]
    area_ha: float
    province: str


@dataclass
class PlantationFireAlert:
    """Alert for fire activity within a plantation concession.

    Attributes:
        concession: Affected concession.
        hotspot_count: Number of hotspots within concession.
        max_frp: Maximum fire radiative power detected.
        severity: Alert severity (CRITICAL/HIGH/MEDIUM/LOW).
        affected_area_pct: Estimated percentage of concession affected.
        detected_at: Timestamp of alert generation.
    """

    concession: PlantationConcession
    hotspot_count: int
    max_frp: float
    severity: str
    affected_area_pct: float
    detected_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


# ── Sample concession registry ──────────────────────────────────────────────

_PLANTATION_CONCESSIONS: list[PlantationConcession] = [
    PlantationConcession("AALI-KAL01", "Astra Agro Lestari", "AALI", "palm_oil",
                         (-2.5, 115.0, -1.5, 116.5), 250_000, "Central Kalimantan"),
    PlantationConcession("LSIP-SUM01", "PP London Sumatra", "LSIP", "palm_oil",
                         (1.0, 103.0, 2.5, 104.5), 120_000, "North Sumatra"),
    PlantationConcession("SIMP-KAL01", "Salim Ivomas Pratama", "SIMP", "palm_oil",
                         (-1.0, 116.0, 0.0, 117.5), 180_000, "East Kalimantan"),
    PlantationConcession("INKP-RIA01", "Indah Kiat Pulp", "INKP", "pulp_paper",
                         (0.5, 101.5, 1.5, 103.0), 300_000, "Riau"),
]


class FireHotspotPlantationOverlay:
    """Overlay NASA FIRMS fire hotspots on plantation concessions.

    Detects fire activity within or near plantation boundaries and
    generates severity-classified alerts for affected listed companies.

    Args:
        firms_api_key: NASA FIRMS API key for data retrieval.
        concessions: List of plantation concessions to monitor.
        buffer_km: Buffer distance around concessions in km.
    """

    def __init__(
        self,
        firms_api_key: str | None = None,
        concessions: list[PlantationConcession] | None = None,
        buffer_km: float = 5.0,
    ) -> None:
        self._api_key = firms_api_key
        self._concessions = concessions or list(_PLANTATION_CONCESSIONS)
        self._buffer_deg = buffer_km / 111.0  # Approximate km to degrees

        logger.info(
            "fire_hotspot_overlay_initialised",
            num_concessions=len(self._concessions),
            buffer_km=buffer_km,
        )

    async def fetch_hotspots(
        self, country: str = "IDN", days: int = 1
    ) -> list[FireHotspot]:
        """Fetch recent fire hotspots from NASA FIRMS API.

        Args:
            country: ISO 3166-1 alpha-3 country code.
            days: Number of days of data to retrieve (max 10).

        Returns:
            List of FireHotspot detections.
        """
        if not self._api_key:
            logger.warning("firms_api_key_not_configured")
            return []

        url = f"{_FIRMS_BASE_URL}/{self._api_key}/VIIRS_SNPP_NRT/{country}/{days}"
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(url)
            response.raise_for_status()

        hotspots: list[FireHotspot] = []
        lines = response.text.strip().split("\n")
        for line in lines[1:]:  # Skip header
            parts = line.split(",")
            if len(parts) < 13:
                continue
            hotspots.append(
                FireHotspot(
                    latitude=float(parts[0]),
                    longitude=float(parts[1]),
                    brightness=float(parts[2]),
                    confidence=int(parts[8]) if parts[8].isdigit() else 50,
                    acquired_at=datetime.now(timezone.utc),
                    satellite="VIIRS_SNPP",
                    frp=float(parts[12]) if parts[12] else 0.0,
                )
            )

        logger.info("firms_hotspots_fetched", count=len(hotspots))
        return hotspots

    def detect_plantation_fires(
        self, hotspots: list[FireHotspot]
    ) -> list[PlantationFireAlert]:
        """Overlay hotspots on concessions and generate alerts.

        Args:
            hotspots: List of fire hotspot detections.

        Returns:
            List of PlantationFireAlert for affected concessions.
        """
        alerts: list[PlantationFireAlert] = []

        for concession in self._concessions:
            min_lat, min_lon, max_lat, max_lon = concession.bbox
            buffered = (
                min_lat - self._buffer_deg,
                min_lon - self._buffer_deg,
                max_lat + self._buffer_deg,
                max_lon + self._buffer_deg,
            )

            matched = [
                h for h in hotspots
                if buffered[0] <= h.latitude <= buffered[2]
                and buffered[1] <= h.longitude <= buffered[3]
            ]

            if not matched:
                continue

            max_frp = max(h.frp for h in matched)
            severity = self._classify_severity(len(matched), max_frp)
            area_pct = min(len(matched) * 0.1, 100.0)

            alert = PlantationFireAlert(
                concession=concession,
                hotspot_count=len(matched),
                max_frp=max_frp,
                severity=severity,
                affected_area_pct=round(area_pct, 2),
            )
            alerts.append(alert)

            logger.info(
                "plantation_fire_detected",
                concession=concession.concession_id,
                ticker=concession.ticker,
                hotspot_count=len(matched),
                severity=severity,
            )

        return alerts

    @staticmethod
    def _classify_severity(hotspot_count: int, max_frp: float) -> str:
        """Classify fire severity from hotspot count and intensity."""
        if hotspot_count >= 50 or max_frp >= 100.0:
            return "CRITICAL"
        elif hotspot_count >= 20 or max_frp >= 50.0:
            return "HIGH"
        elif hotspot_count >= 5:
            return "MEDIUM"
        return "LOW"
