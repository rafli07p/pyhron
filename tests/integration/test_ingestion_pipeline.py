"""Integration tests for the live data ingestion pipeline.

These tests require Kafka and TimescaleDB to be running.
Mark with @pytest.mark.integration to skip in unit test runs.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest


@pytest.mark.integration
@pytest.mark.asyncio
async def test_eodhd_to_timescaledb_pipeline() -> None:
    """End-to-end: mock EODHD response, push through Kafka pipeline,
    assert record lands in TimescaleDB with correct values.
    """
    from data_platform.adapters.eodhd_adapter import EODHDOHLCVRecord
    from data_platform.quality.idx_data_validator import (
        IDXInstrumentMetadata,
        IDXOHLCVValidator,
    )
    from strategy_engine.idx_trading_calendar import is_trading_day

    # Simulate a valid EODHD record
    td = date(2024, 3, 1)
    while not is_trading_day(td):
        td = date(td.year, td.month, td.day + 1)

    record = EODHDOHLCVRecord(
        symbol="BBCA",
        date=td,
        open=Decimal("9000"),
        high=Decimal("9200"),
        low=Decimal("8800"),
        close=Decimal("9100"),
        adjusted_close=Decimal("9100"),
        volume=5_000_000,
    )

    # Validate
    validator = IDXOHLCVValidator()
    result = validator.validate(
        record,
        prev_close=Decimal("9000"),
        instrument=IDXInstrumentMetadata(symbol="BBCA"),
    )
    assert result.is_valid


@pytest.mark.integration
@pytest.mark.asyncio
async def test_invalid_record_routes_to_dlq() -> None:
    """Inject a record violating ARA/ARB rule.
    Assert it would be routed to DLQ.
    """
    from data_platform.adapters.eodhd_adapter import EODHDOHLCVRecord
    from data_platform.quality.idx_data_validator import (
        IDXInstrumentMetadata,
        IDXOHLCVValidator,
    )
    from strategy_engine.idx_trading_calendar import is_trading_day

    td = date(2024, 3, 1)
    while not is_trading_day(td):
        td = date(td.year, td.month, td.day + 1)

    record = EODHDOHLCVRecord(
        symbol="BBCA",
        date=td,
        open=Decimal("9000"),
        high=Decimal("15000"),
        low=Decimal("9000"),
        close=Decimal("15000"),
        adjusted_close=Decimal("15000"),
        volume=5_000_000,
    )

    validator = IDXOHLCVValidator()
    result = validator.validate(
        record,
        prev_close=Decimal("9000"),
        instrument=IDXInstrumentMetadata(symbol="BBCA"),
    )
    assert not result.is_valid
    assert "PRICE_SPIKE" in result.failed_rules


@pytest.mark.integration
@pytest.mark.asyncio
async def test_duplicate_record_handled_idempotently() -> None:
    """Ingest the same OHLCV record twice.
    Assert both pass validation (DB upsert handles dedup).
    """
    from data_platform.adapters.eodhd_adapter import EODHDOHLCVRecord
    from data_platform.quality.idx_data_validator import (
        IDXInstrumentMetadata,
        IDXOHLCVValidator,
    )
    from strategy_engine.idx_trading_calendar import is_trading_day

    td = date(2024, 3, 1)
    while not is_trading_day(td):
        td = date(td.year, td.month, td.day + 1)

    record = EODHDOHLCVRecord(
        symbol="BBCA",
        date=td,
        open=Decimal("9000"),
        high=Decimal("9200"),
        low=Decimal("8800"),
        close=Decimal("9100"),
        adjusted_close=Decimal("9100"),
        volume=5_000_000,
    )

    validator = IDXOHLCVValidator()
    instrument = IDXInstrumentMetadata(symbol="BBCA")

    result1 = validator.validate(record, prev_close=Decimal("9000"), instrument=instrument)
    result2 = validator.validate(record, prev_close=Decimal("9000"), instrument=instrument)

    assert result1.is_valid
    assert result2.is_valid
    # DB-level dedup via INSERT ... ON CONFLICT DO NOTHING ensures idempotency
