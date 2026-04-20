"""BMKG (Badan Meteorologi, Klimatologi, dan Geofisika) daily rainfall ingestion.

Source: BMKG Open Data API (``dataonline.bmkg.go.id``)

Design:
  - Daily rainfall per province / station
  - Covers 34 Indonesian provinces
  - Idempotent upsert keyed on (station_id, observation_date)
  - Used as input for CPO yield models and flood-risk analytics
"""

from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from typing import Any

import httpx
from sqlalchemy import text

from shared.async_database_session import get_session
from shared.configuration_settings import get_config
from shared.platform_exception_hierarchy import (
    DataQualityError,
    IngestionError,
)
from shared.prometheus_metrics_registry import INGESTION_ROWS
from shared.structured_json_logger import get_logger

logger = get_logger(__name__)

BMKG_API_BASE = "https://dataonline.bmkg.go.id/akses_data"
BMKG_OPEN_DATA_URL = "https://data.bmkg.go.id/DataMKG/MEWS/DigitalForecast"
MAX_RETRIES = 3

# Representative BMKG stations (one per major province)
BMKG_STATIONS: dict[str, str] = {
    "96745": "Jakarta - Kemayoran",
    "96749": "Tangerang - Soekarno Hatta",
    "96839": "Surabaya - Juanda",
    "96753": "Bandung - Husein Sastranegara",
    "96783": "Semarang - Ahmad Yani",
    "96011": "Medan - Kualanamu",
    "96163": "Palembang - Sultan Mahmud Badaruddin II",
    "96295": "Pontianak - Supadio",
    "97180": "Makassar - Sultan Hasanuddin",
    "97230": "Denpasar - Ngurah Rai",
}


@dataclass
class IngestionResult:
    """Outcome of an ingestion run."""

    source: str
    rows_inserted: int = 0
    rows_updated: int = 0
    rows_skipped: int = 0
    errors: list[str] = field(default_factory=list)
    duration_ms: float = 0.0


class BMKGDailyRainfallIngester:
    """Daily rainfall ingester from BMKG.

    Fetches daily precipitation data from BMKG stations across Indonesian
    provinces and persists it for use in climate-sensitive analytics
    (CPO yields, flood risk, etc.).

    Usage::

        ingester = BMKGDailyRainfallIngester()
        result = await ingester.ingest_for_date_range(
            start=date(2024, 1, 1),
            end=date(2024, 12, 31),
        )
    """

    def __init__(self) -> None:
        self._config = get_config()
        self._logger = get_logger(__name__)

    # Public API

    async def ingest_for_date_range(
        self,
        start: date,
        end: date,
        station_ids: list[str] | None = None,
    ) -> IngestionResult:
        """Ingest daily rainfall data over [start, end].

        Args:
            start: First calendar date (inclusive).
            end: Last calendar date (inclusive).
            station_ids: BMKG station IDs to fetch; defaults to all known.

        Returns:
            An ``IngestionResult`` summarising the run.
        """
        t0 = time.monotonic()
        result = IngestionResult(source="bmkg")
        targets = station_ids or list(BMKG_STATIONS.keys())

        all_records: list[dict[str, Any]] = []
        for station_id in targets:
            try:
                records = await self._fetch_station_rainfall(station_id, start, end)
                all_records.extend(records)
            except IngestionError as exc:
                result.errors.append(f"Station {station_id}: {exc}")

        valid: list[dict[str, Any]] = []
        for rec in all_records:
            try:
                self._validate_record(rec)
                valid.append(rec)
            except DataQualityError as exc:
                result.errors.append(str(exc))
                result.rows_skipped += 1

        inserted, updated = await self._upsert_records(valid)
        result.rows_inserted = inserted
        result.rows_updated = updated
        result.duration_ms = (time.monotonic() - t0) * 1000

        INGESTION_ROWS.labels(source="bmkg", symbol="RAINFALL", operation="inserted").inc(inserted)

        self._logger.info(
            "bmkg_rainfall_ingestion_complete",
            stations=len(targets),
            rows_inserted=inserted,
            rows_updated=updated,
            duration_ms=round(result.duration_ms, 2),
        )
        return result

    # Data fetch

    async def _fetch_station_rainfall(
        self,
        station_id: str,
        start: date,
        end: date,
    ) -> list[dict[str, Any]]:
        """Fetch daily rainfall for a single BMKG station.

        Args:
            station_id: BMKG station identifier.
            start: Start date.
            end: End date.

        Returns:
            Normalised rainfall records.

        Raises:
            IngestionError: On fetch failure.
        """
        headers = {
            "User-Agent": "Pyhron/1.0 (Data Platform)",
            "Accept": "application/json,text/xml",
        }
        params = {
            "station_id": station_id,
            "start_date": start.isoformat(),
            "end_date": end.isoformat(),
            "parameter": "rainfall",
        }

        for attempt in range(1, MAX_RETRIES + 1):
            try:
                async with httpx.AsyncClient(timeout=30.0) as client:
                    resp = await client.get(BMKG_API_BASE, params=params, headers=headers)
                    resp.raise_for_status()
                    return self._parse_rainfall_response(resp.json(), station_id, start, end)
            except httpx.HTTPStatusError as exc:
                if exc.response.status_code in (500, 502, 503) and attempt < MAX_RETRIES:
                    await asyncio.sleep(2 ** (attempt - 1))
                    continue
                raise IngestionError(f"BMKG API error for station {station_id}: {exc}") from exc
            except httpx.RequestError as exc:
                if attempt < MAX_RETRIES:
                    await asyncio.sleep(2 ** (attempt - 1))
                    continue
                raise IngestionError(f"BMKG connection error for station {station_id}: {exc}") from exc

        raise IngestionError(f"BMKG fetch failed for station {station_id} after {MAX_RETRIES} retries")

    # Parsing

    def _parse_rainfall_response(
        self,
        data: dict[str, Any] | list[Any],
        station_id: str,
        start: date,
        end: date,
    ) -> list[dict[str, Any]]:
        """Parse BMKG rainfall response into normalised records.

        Args:
            data: Raw API response.
            station_id: BMKG station ID.
            start: Start date filter.
            end: End date filter.

        Returns:
            List of normalised rainfall records.
        """
        records: list[dict[str, Any]] = []
        items = data.get("data", data) if isinstance(data, dict) else data

        for item in items:
            try:
                obs_date = date.fromisoformat(item.get("date", item.get("tanggal", ""))[:10])
            except (ValueError, TypeError):
                continue

            if obs_date < start or obs_date > end:
                continue

            rainfall = item.get("rainfall") or item.get("curah_hujan")
            if rainfall is None:
                continue

            records.append(
                {
                    "station_id": station_id,
                    "station_name": BMKG_STATIONS.get(station_id, "Unknown"),
                    "observation_date": obs_date,
                    "rainfall_mm": Decimal(str(rainfall)),
                    "temperature_max_c": Decimal(str(item.get("temp_max", 0) or 0)),
                    "temperature_min_c": Decimal(str(item.get("temp_min", 0) or 0)),
                    "humidity_pct": Decimal(str(item.get("humidity", 0) or 0)),
                }
            )

        return records

    # Validation

    def _validate_record(self, record: dict[str, Any]) -> None:
        """Validate a rainfall record.

        Raises:
            DataQualityError: If validation fails.
        """
        rainfall = float(record["rainfall_mm"])
        if rainfall < 0:
            raise DataQualityError(
                f"Negative rainfall {rainfall} mm at station {record['station_id']} on {record['observation_date']}"
            )
        # World record daily rainfall is ~1825mm; use 500mm as practical max
        if rainfall > 500:
            raise DataQualityError(
                f"Implausible rainfall {rainfall} mm at station {record['station_id']} on {record['observation_date']}"
            )

    # Persistence

    async def _upsert_records(
        self,
        records: list[dict[str, Any]],
    ) -> tuple[int, int]:
        """Upsert rainfall records into ``weather_observations``.

        Returns:
            Tuple of (inserted, updated) counts.
        """
        if not records:
            return 0, 0

        inserted = 0
        updated = 0

        async with get_session() as session:
            for rec in records:
                result = await session.execute(
                    text("""
                        INSERT INTO weather_observations
                            (station_id, station_name, observation_date,
                             rainfall_mm, temperature_max_c, temperature_min_c,
                             humidity_pct, source, updated_at)
                        VALUES
                            (:station_id, :station_name, :observation_date,
                             :rainfall_mm, :temperature_max_c, :temperature_min_c,
                             :humidity_pct, 'bmkg', NOW())
                        ON CONFLICT (station_id, observation_date) DO UPDATE SET
                            rainfall_mm = EXCLUDED.rainfall_mm,
                            temperature_max_c = EXCLUDED.temperature_max_c,
                            temperature_min_c = EXCLUDED.temperature_min_c,
                            humidity_pct = EXCLUDED.humidity_pct,
                            updated_at = NOW()
                        RETURNING (xmax = 0) AS is_insert
                    """),
                    {
                        "station_id": rec["station_id"],
                        "station_name": rec["station_name"],
                        "observation_date": rec["observation_date"],
                        "rainfall_mm": float(rec["rainfall_mm"]),
                        "temperature_max_c": float(rec["temperature_max_c"]),
                        "temperature_min_c": float(rec["temperature_min_c"]),
                        "humidity_pct": float(rec["humidity_pct"]),
                    },
                )
                is_insert = result.scalar()
                if is_insert:
                    inserted += 1
                else:
                    updated += 1

        return inserted, updated
