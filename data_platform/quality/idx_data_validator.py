"""IDX data validation for OHLCV and fundamental records.

Every record must pass validation before being written to the database
or published to Kafka. Failed records go to the dead letter queue.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from typing import Any

from data_platform.adapters.eodhd_adapter import EODHDOHLCVRecord
from shared.structured_json_logger import get_logger
from strategy_engine.idx_trading_calendar import is_trading_day

logger = get_logger(__name__)

IDX_MAX_PRICE_MOVE = Decimal("0.35")
IDX_TICK_SIZE_MAP: dict[tuple[Decimal, Decimal], Decimal] = {
    (Decimal("0"), Decimal("199")): Decimal("1"),
    (Decimal("200"), Decimal("499")): Decimal("2"),
    (Decimal("500"), Decimal("1999")): Decimal("5"),
    (Decimal("2000"), Decimal("4999")): Decimal("10"),
    (Decimal("5000"), Decimal("99999")): Decimal("25"),
}


@dataclass
class IDXInstrumentMetadata:
    """Minimal instrument metadata needed for validation."""

    symbol: str
    is_active: bool = True
    avg_daily_volume: int = 0


@dataclass
class ValidationResult:
    is_valid: bool
    record: EODHDOHLCVRecord
    failed_rules: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    adjusted_record: EODHDOHLCVRecord | None = None


def _get_tick_size(price: Decimal) -> Decimal:
    """Look up the IDX tick size for a given price tier."""
    for (low, high), tick in IDX_TICK_SIZE_MAP.items():
        if low <= price <= high:
            return tick
    return Decimal("25")


class IDXOHLCVValidator:
    """Validates OHLCV records against IDX-specific and statistical rules."""

    def validate(
        self,
        record: EODHDOHLCVRecord,
        prev_close: Decimal | None,
        instrument: IDXInstrumentMetadata,
    ) -> ValidationResult:
        """Apply all validation rules. Return ValidationResult."""
        failed_rules: list[str] = []
        warnings: list[str] = []
        adjusted_record: EODHDOHLCVRecord | None = None

        # Rule 1: OHLC internal consistency
        if record.high < record.open or record.high < record.close or record.high < record.low:
            failed_rules.append("OHLC_INCONSISTENCY")
        if record.low > record.open or record.low > record.close:
            failed_rules.append("OHLC_INCONSISTENCY")
        if record.open <= 0 or record.high <= 0 or record.low <= 0 or record.close <= 0:
            failed_rules.append("NON_POSITIVE_PRICE")

        # Rule 2: IDX ARA/ARB circuit breaker
        if prev_close is not None and prev_close > 0:
            pct_move = abs(record.close / prev_close - 1)
            if pct_move > IDX_MAX_PRICE_MOVE:
                failed_rules.append("PRICE_SPIKE")
                logger.warning(
                    "ara_arb_violation",
                    symbol=record.symbol,
                    date=str(record.date),
                    close=str(record.close),
                    prev_close=str(prev_close),
                    pct_move=f"{pct_move:.4f}",
                )

        # Rule 3: Volume sanity
        if record.volume < 0:
            failed_rules.append("NEGATIVE_VOLUME")
        elif record.volume == 0 and is_trading_day(record.date):
            warnings.append("ZERO_VOLUME_WARNING")
        if instrument.avg_daily_volume > 0 and record.volume > instrument.avg_daily_volume * 50:
            warnings.append("VOLUME_SPIKE_WARNING")

        # Rule 4: Price precision / tick size conformance
        tick = _get_tick_size(record.close)
        if record.close % tick != 0:
            rounded = round(record.close / tick) * tick
            warnings.append("TICK_ADJUSTED")
            adjusted_record = EODHDOHLCVRecord(
                symbol=record.symbol,
                date=record.date,
                open=record.open,
                high=record.high,
                low=record.low,
                close=rounded,
                adjusted_close=record.adjusted_close,
                volume=record.volume,
                source=record.source,
            )

        # Rule 5: Trading day check
        if not is_trading_day(record.date):
            failed_rules.append("NON_TRADING_DAY")

        # Deduplicate failed_rules
        failed_rules = list(dict.fromkeys(failed_rules))

        is_valid = len(failed_rules) == 0
        return ValidationResult(
            is_valid=is_valid,
            record=record,
            failed_rules=failed_rules,
            warnings=warnings,
            adjusted_record=adjusted_record,
        )


class IDXFundamentalsValidator:
    """Validate fundamental data records."""

    def validate(
        self,
        record: dict[str, Any],
        symbol: str,
    ) -> ValidationResult:
        """Validate fundamental data record."""
        failed_rules: list[str] = []
        warnings: list[str] = []

        revenue = record.get("revenue")
        if revenue is not None and revenue < 0:
            warnings.append("NEGATIVE_REVENUE")

        total_assets = record.get("totalAssets") or record.get("total_assets")
        if total_assets is not None and total_assets <= 0:
            failed_rules.append("INVALID_TOTAL_ASSETS")

        # Dates: fiscal period end must be in the past
        period_end = record.get("period_end") or record.get("fiscal_date")
        if period_end:
            try:
                if isinstance(period_end, str):
                    period_end = date.fromisoformat(period_end)
                if period_end > date.today():
                    failed_rules.append("FUTURE_PERIOD_END")
            except (ValueError, TypeError):
                failed_rules.append("INVALID_PERIOD_DATE")

        # Ratios derived from zero denominators: set to None, log warning
        total_equity = record.get("totalEquity") or record.get("total_equity")
        if total_equity is not None and total_equity == 0:
            warnings.append("ZERO_EQUITY_DENOMINATOR")

        # Use a dummy record for the ValidationResult
        dummy = EODHDOHLCVRecord(
            symbol=symbol,
            date=date.today(),
            open=Decimal("0"),
            high=Decimal("0"),
            low=Decimal("0"),
            close=Decimal("0"),
            adjusted_close=Decimal("0"),
            volume=0,
            source="fundamentals",
        )

        return ValidationResult(
            is_valid=len(failed_rules) == 0,
            record=dummy,
            failed_rules=failed_rules,
            warnings=warnings,
        )
