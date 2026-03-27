"""Unit tests for IDX trading calendar utilities.

Tests:
  - Weekends (Saturday, Sunday) are non-trading days
  - Indonesian national holidays are non-trading days
  - T+2 settlement date calculation skips weekends and holidays
"""

from __future__ import annotations

from datetime import date, timedelta

import pytest

# Calendar Utilities (pure functions under test)
# Indonesian public holidays for 2025 (subset for testing)
IDX_HOLIDAYS_2025: set[date] = {
    date(2025, 1, 1),  # New Year
    date(2025, 1, 29),  # Isra Mi'raj
    date(2025, 1, 30),  # Chinese New Year (observed)
    date(2025, 3, 31),  # Hari Raya Nyepi
    date(2025, 4, 18),  # Good Friday
    date(2025, 5, 1),  # Labour Day
    date(2025, 5, 12),  # Waisak
    date(2025, 5, 29),  # Ascension Day
    date(2025, 6, 1),  # Pancasila Day
    date(2025, 8, 17),  # Independence Day
    date(2025, 12, 25),  # Christmas Day
}


def is_trading_day(d: date, holidays: set[date] | None = None) -> bool:
    """Check if a date is an IDX trading day (not weekend, not holiday)."""
    if d.weekday() >= 5:  # Saturday=5, Sunday=6
        return False
    hols = holidays if holidays is not None else IDX_HOLIDAYS_2025
    return d not in hols


def next_trading_day(d: date, holidays: set[date] | None = None) -> date:
    """Return the next trading day after the given date."""
    current = d + timedelta(days=1)
    while not is_trading_day(current, holidays):
        current += timedelta(days=1)
    return current


def compute_settlement_date_idx(
    trade_date: date,
    settlement_days: int = 2,
    holidays: set[date] | None = None,
) -> date:
    """Compute T+N settlement date, skipping weekends and IDX holidays."""
    days_added = 0
    current = trade_date
    while days_added < settlement_days:
        current += timedelta(days=1)
        if is_trading_day(current, holidays):
            days_added += 1
    return current


# Weekend Tests
class TestWeekends:
    def test_monday_is_trading_day(self):
        assert is_trading_day(date(2025, 1, 6)) is True  # Monday

    def test_friday_is_trading_day(self):
        assert is_trading_day(date(2025, 1, 10)) is True  # Friday

    def test_saturday_is_not_trading_day(self):
        assert is_trading_day(date(2025, 1, 11)) is False  # Saturday

    def test_sunday_is_not_trading_day(self):
        assert is_trading_day(date(2025, 1, 12)) is False  # Sunday

    @pytest.mark.parametrize("day_offset", range(7))
    def test_weekday_classification(self, day_offset):
        d = date(2025, 1, 6) + timedelta(days=day_offset)  # Mon Jan 6
        if d.weekday() < 5:
            assert is_trading_day(d, holidays=set()) is True
        else:
            assert is_trading_day(d, holidays=set()) is False


# Holiday Tests
class TestHolidays:
    def test_new_year_is_holiday(self):
        assert is_trading_day(date(2025, 1, 1)) is False

    def test_independence_day_is_holiday(self):
        assert is_trading_day(date(2025, 8, 17)) is False

    def test_christmas_is_holiday(self):
        assert is_trading_day(date(2025, 12, 25)) is False

    def test_regular_weekday_not_holiday(self):
        assert is_trading_day(date(2025, 1, 2)) is True  # Jan 2 is Thursday

    def test_next_trading_day_skips_holiday(self):
        # Dec 24 (Wed) -> skip Dec 25 (holiday) -> Dec 26 (Fri)
        assert next_trading_day(date(2025, 12, 24)) == date(2025, 12, 26)


# T+2 Settlement Tests
class TestSettlementDate:
    def test_monday_trade_settles_wednesday(self):
        # Mon Jan 6 -> T+2 = Wed Jan 8
        result = compute_settlement_date_idx(date(2025, 1, 6))
        assert result == date(2025, 1, 8)

    def test_thursday_trade_settles_monday(self):
        # Thu Jan 9 -> Fri Jan 10 (T+1) -> Mon Jan 13 (T+2, skips weekend)
        result = compute_settlement_date_idx(date(2025, 1, 9))
        assert result == date(2025, 1, 13)

    def test_friday_trade_settles_tuesday(self):
        # Fri Jan 10 -> skip Sat/Sun -> Mon Jan 13 (T+1) -> Tue Jan 14 (T+2)
        result = compute_settlement_date_idx(date(2025, 1, 10))
        assert result == date(2025, 1, 14)

    def test_settlement_skips_holiday(self):
        # Trade on Wed Dec 24 -> Dec 25 is holiday -> Dec 26 (T+1) -> Dec 29 Mon (T+2)
        result = compute_settlement_date_idx(date(2025, 12, 24))
        assert result == date(2025, 12, 29)

    def test_settlement_skips_weekend_and_holiday(self):
        # Trade on Thu Apr 17 -> Apr 18 is Good Friday (holiday) ->
        # skip Sat/Sun -> Mon Apr 21 (T+1) -> Tue Apr 22 (T+2)
        result = compute_settlement_date_idx(date(2025, 4, 17))
        assert result == date(2025, 4, 22)
