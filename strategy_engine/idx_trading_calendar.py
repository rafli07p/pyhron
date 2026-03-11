"""IDX (Indonesia Stock Exchange) trading calendar utilities.

IDX trading hours: 09:00-16:00 WIB (UTC+7)
  Session 1: 09:00-12:00
  Session 2: 13:30-16:00
  Pre-opening: 08:45-09:00

Regular trading days: Monday-Friday
Closed: Indonesian national holidays (Hari Libur Nasional)

Source: Pengumuman BEI re: Hari Libur Bursa
"""

from __future__ import annotations

from datetime import date, timedelta
from functools import lru_cache

# IDX market holidays 2024-2026
# Update annually from: https://www.idx.co.id/investor/hari-libur-bursa/
IDX_MARKET_HOLIDAYS: frozenset[date] = frozenset(
    [
        # 2024
        date(2024, 1, 1),
        date(2024, 2, 8),
        date(2024, 2, 9),
        date(2024, 2, 14),
        date(2024, 3, 11),
        date(2024, 3, 29),
        date(2024, 4, 8),
        date(2024, 4, 9),
        date(2024, 4, 10),
        date(2024, 4, 11),
        date(2024, 4, 12),
        date(2024, 5, 1),
        date(2024, 5, 9),
        date(2024, 5, 23),
        date(2024, 5, 24),
        date(2024, 6, 17),
        date(2024, 6, 18),
        date(2024, 7, 19),
        date(2024, 8, 17),
        date(2024, 9, 16),
        date(2024, 12, 25),
        date(2024, 12, 26),
        # 2025
        date(2025, 1, 1),
        date(2025, 1, 27),
        date(2025, 1, 28),
        date(2025, 1, 29),
        date(2025, 3, 28),
        date(2025, 3, 29),
        date(2025, 3, 31),
        date(2025, 4, 1),
        date(2025, 4, 2),
        date(2025, 4, 18),
        date(2025, 5, 1),
        date(2025, 5, 12),
        date(2025, 5, 13),
        date(2025, 5, 29),
        date(2025, 6, 1),
        date(2025, 6, 6),
        date(2025, 6, 27),
        date(2025, 8, 17),
        date(2025, 9, 5),
        date(2025, 12, 25),
        date(2025, 12, 26),
        # 2026
        date(2026, 1, 1),
        date(2026, 1, 16),
        date(2026, 3, 3),
        date(2026, 3, 20),
        date(2026, 4, 2),
        date(2026, 4, 3),
    ]
)


def is_trading_day(d: date) -> bool:
    """Check if a date is an IDX trading day."""
    return d.weekday() < 5 and d not in IDX_MARKET_HOLIDAYS


def next_trading_day(d: date) -> date:
    """Return the next trading day strictly after *d*."""
    candidate = d + timedelta(days=1)
    while not is_trading_day(candidate):
        candidate += timedelta(days=1)
    return candidate


def prev_trading_day(d: date) -> date:
    """Return the most recent trading day strictly before *d*."""
    candidate = d - timedelta(days=1)
    while not is_trading_day(candidate):
        candidate -= timedelta(days=1)
    return candidate


@lru_cache(maxsize=256)
def get_monthly_rebalance_dates(
    start_date: date,
    end_date: date,
) -> tuple[date, ...]:
    """Return the first trading day of each month between *start* and *end*.

    These are the dates when momentum signals are generated and rebalancing
    orders are submitted.  Returns a tuple (hashable) for LRU caching.
    """
    dates: list[date] = []
    # Start from the first day of start_date's month
    current = date(start_date.year, start_date.month, 1)
    while current <= end_date:
        # Find the first trading day of this month
        candidate = current
        while not is_trading_day(candidate):
            candidate += timedelta(days=1)
        if start_date <= candidate <= end_date:
            dates.append(candidate)
        # Move to next month
        if current.month == 12:
            current = date(current.year + 1, 1, 1)
        else:
            current = date(current.year, current.month + 1, 1)
    return tuple(dates)


def trading_days_between(start: date, end: date) -> int:
    """Count trading days between two dates (exclusive of *end*)."""
    count = 0
    current = start
    while current < end:
        if is_trading_day(current):
            count += 1
        current += timedelta(days=1)
    return count


def get_settlement_date(trade_date: date) -> date:
    """T+2 settlement: 2 business days after trade date."""
    days_added = 0
    current = trade_date
    while days_added < 2:
        current += timedelta(days=1)
        if is_trading_day(current):
            days_added += 1
    return current
