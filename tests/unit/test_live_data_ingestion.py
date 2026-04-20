"""Tests for the live data ingestion pipeline.

10 unit tests covering:
- OHLCV validation (ARA/ARB, consistency, trading day)
- Corporate action adjustment factors
- Data quality monitoring
- Backfill date computation
- DLQ processing
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock

import pytest

from data_platform.adapters.eodhd_adapter import (
    EODHDDividendRecord,
    EODHDOHLCVRecord,
    EODHDSplitRecord,
)
from data_platform.equity_ingestion.action_processor import (
    IDXCorporateActionProcessor,
)
from data_platform.quality.idx_data_validator import (
    IDXInstrumentMetadata,
    IDXOHLCVValidator,
)
from scripts.backfill_historical_data import compute_missing_dates
from strategy_engine.idx_trading_calendar import is_trading_day


def mock_instrument(symbol: str) -> IDXInstrumentMetadata:
    return IDXInstrumentMetadata(symbol=symbol, is_active=True, avg_daily_volume=1_000_000)


def make_valid_ohlcv_record(symbol: str, trade_date: date) -> EODHDOHLCVRecord:
    return EODHDOHLCVRecord(
        symbol=symbol,
        date=trade_date,
        open=Decimal("9000"),
        high=Decimal("9200"),
        low=Decimal("8800"),
        close=Decimal("9100"),
        adjusted_close=Decimal("9100"),
        volume=5_000_000,
    )


# Test 1: OHLCV validation rejects ARA/ARB violation
def test_ara_arb_violation_rejected() -> None:
    validator = IDXOHLCVValidator()
    # Find a valid trading day
    td = date(2024, 3, 1)
    while not is_trading_day(td):
        td = date(td.year, td.month, td.day + 1)

    record = EODHDOHLCVRecord(
        symbol="BBCA",
        date=td,
        open=Decimal("9000"),
        high=Decimal("13000"),
        low=Decimal("9000"),
        close=Decimal("13000"),
        adjusted_close=Decimal("13000"),
        volume=1000000,
    )
    result = validator.validate(record, prev_close=Decimal("9000"), instrument=mock_instrument("BBCA"))
    assert not result.is_valid
    assert "PRICE_SPIKE" in result.failed_rules


# Test 2: OHLCV validation accepts valid record
def test_valid_ohlcv_record_passes() -> None:
    validator = IDXOHLCVValidator()
    td = date(2024, 3, 1)
    while not is_trading_day(td):
        td = date(td.year, td.month, td.day + 1)

    record = make_valid_ohlcv_record("BBCA", td)
    result = validator.validate(record, prev_close=Decimal("9000"), instrument=mock_instrument("BBCA"))
    assert result.is_valid
    assert result.failed_rules == []


# Test 3: OHLCV validation detects internal inconsistency
def test_ohlcv_high_less_than_low_rejected() -> None:
    validator = IDXOHLCVValidator()
    td = date(2024, 3, 1)
    while not is_trading_day(td):
        td = date(td.year, td.month, td.day + 1)

    record = make_valid_ohlcv_record("BBCA", td)
    record.high = Decimal("8000")
    record.low = Decimal("9000")
    result = validator.validate(record, prev_close=Decimal("9000"), instrument=mock_instrument("BBCA"))
    assert not result.is_valid


# Test 4: Non-trading day rejected
def test_non_trading_day_rejected() -> None:
    validator = IDXOHLCVValidator()
    record = make_valid_ohlcv_record("BBCA", date(2024, 12, 25))
    result = validator.validate(record, prev_close=Decimal("9000"), instrument=mock_instrument("BBCA"))
    assert not result.is_valid
    assert "NON_TRADING_DAY" in result.failed_rules


# Test 5: Split adjustment factor calculation
def test_split_adjustment_factor_2for1() -> None:
    processor = IDXCorporateActionProcessor()
    split = EODHDSplitRecord(symbol="BBCA", date=date(2024, 6, 1), split_ratio=Decimal("2"))
    factor = processor.compute_adjustment_factor(split, close_before_action=Decimal("10000"))
    assert factor == Decimal("0.5")


# Test 6: Dividend adjustment factor calculation
def test_dividend_adjustment_factor() -> None:
    processor = IDXCorporateActionProcessor()
    dividend = EODHDDividendRecord(
        symbol="BBCA",
        ex_date=date(2024, 6, 1),
        payment_date=None,
        dividend_idr=Decimal("200"),
        dividend_type="cash",
    )
    factor = processor.compute_adjustment_factor(dividend, close_before_action=Decimal("10000"))
    assert factor == Decimal("0.98")


# Test 7: Coverage report detects missing symbols
@pytest.mark.asyncio
async def test_coverage_report_detects_missing() -> None:
    from data_platform.quality.idx_data_quality_monitor import IDXDataQualityMonitor

    monitor = IDXDataQualityMonitor()

    # Mock DB session
    mock_db = AsyncMock()

    # Active instruments: BBCA, BBRI, GOTO, BUKA
    active_result = MagicMock()
    active_result.fetchall.return_value = [("BBCA",), ("BBRI",), ("GOTO",), ("BUKA",)]

    # Only BBCA and BBRI have data
    data_result = MagicMock()
    data_result.fetchall.return_value = [("BBCA",), ("BBRI",)]

    mock_db.execute = AsyncMock(side_effect=[active_result, data_result])

    report = await monitor.compute_coverage(trade_date=date(2024, 3, 1), db_session=mock_db)
    assert "GOTO" in report.missing_symbols
    assert "BUKA" in report.missing_symbols
    assert report.coverage_pct < 1.0


# Test 8: Gap detection identifies missing trading days
@pytest.mark.asyncio
async def test_gap_detection_finds_missing_dates() -> None:
    from datetime import timedelta

    from data_platform.quality.idx_data_quality_monitor import IDXDataQualityMonitor

    monitor = IDXDataQualityMonitor()
    mock_db = AsyncMock()

    # Build expected trading days for the last ~20 calendar days
    today = date.today()
    start = today - timedelta(days=20)
    all_trading_days = []
    d = start
    while d <= today:
        if is_trading_day(d):
            all_trading_days.append(d)
        d += timedelta(days=1)

    # Pick a gap date in the middle of the trading days
    if len(all_trading_days) < 5:
        # Not enough trading days to test; skip
        return
    gap_date = all_trading_days[len(all_trading_days) // 2]

    # Provide all recent dates except the gap date
    db_dates = [(td,) for td in all_trading_days if td != gap_date]

    data_result = MagicMock()
    data_result.fetchall.return_value = db_dates
    mock_db.execute = AsyncMock(return_value=data_result)

    gaps = await monitor.detect_gaps(symbol="BBCA", lookback_days=10, db_session=mock_db)
    assert gap_date in gaps


# Test 9: Backfill skips existing records
def test_backfill_skips_existing_data() -> None:
    # Find valid trading days in Jan 2024
    from datetime import timedelta

    existing_dates: set[date] = set()
    d = date(2024, 1, 1)
    trading_days_found = 0
    while trading_days_found < 2 and d < date(2024, 1, 31):
        if is_trading_day(d):
            existing_dates.add(d)
            trading_days_found += 1
        d += timedelta(days=1)

    to_fetch = compute_missing_dates(
        symbol="BBCA",
        date_from=date(2024, 1, 1),
        date_to=date(2024, 1, 31),
        existing_dates=existing_dates,
    )
    for existing in existing_dates:
        assert existing not in to_fetch


# Test 10: DLQ processor retries up to max then marks permanent


@pytest.mark.asyncio
async def test_dlq_max_retries_marks_permanent() -> None:
    from data_platform.consumers.dlq_processor import DLQProcessor

    mock_db = AsyncMock()
    processor = DLQProcessor(db_session=mock_db, kafka_bootstrap_servers="localhost:9092")

    invalid_record = {
        "original_record": {
            "symbol": "FAKE",
            "date": "2024-01-01",
            "open": "100",
            "high": "200",
            "low": "50",
            "close": "150",
            "volume": 0,
        },
        "failed_rules": ["PRICE_SPIKE"],
        "retry_count": 3,
    }

    result = await processor.process_record(
        record=invalid_record,
        topic="pyhron.dlq.eod_ohlcv",
        retry_count=3,
    )
    assert result.disposition == "permanent"
    # Verify DB write was attempted
    mock_db.execute.assert_called_once()
    mock_db.flush.assert_called_once()
