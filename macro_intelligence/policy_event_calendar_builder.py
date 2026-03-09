"""Policy event and earnings calendar builder.

Aggregates scheduled macro-economic events and corporate earnings
dates into a unified calendar for investment decision support.

Covers:
  - Bank Indonesia (BI) rate decisions (monthly RDG schedule).
  - BPS data releases (GDP, inflation, trade balance).
  - FOMC decisions (impact on USD/IDR and capital flows).
  - IDX corporate earnings season dates.
  - OJK regulatory announcements.

Usage::

    builder = PolicyEventCalendarBuilder()
    calendar = builder.build_calendar(start_date, end_date)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any

from shared.structured_json_logger import get_logger

logger = get_logger(__name__)


class EventType(str, Enum):
    """Calendar event type classification."""

    BI_RATE_DECISION = "BI_RATE_DECISION"
    GDP_RELEASE = "GDP_RELEASE"
    INFLATION_RELEASE = "INFLATION_RELEASE"
    TRADE_BALANCE = "TRADE_BALANCE"
    FOMC_DECISION = "FOMC_DECISION"
    EARNINGS_SEASON = "EARNINGS_SEASON"
    OJK_REGULATION = "OJK_REGULATION"
    IDX_REBALANCE = "IDX_REBALANCE"
    BOND_AUCTION = "BOND_AUCTION"


class EventImpact(str, Enum):
    """Expected market impact level."""

    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


@dataclass
class CalendarEvent:
    """Single calendar event.

    Attributes:
        event_type: Type of event.
        title: Human-readable title.
        scheduled_at: Scheduled datetime (UTC).
        impact: Expected market impact.
        affected_assets: Asset classes or tickers likely affected.
        description: Event description.
        previous_value: Previous period value (if applicable).
        consensus: Market consensus (if available).
    """

    event_type: EventType
    title: str
    scheduled_at: datetime
    impact: EventImpact
    affected_assets: list[str] = field(default_factory=list)
    description: str = ""
    previous_value: str | None = None
    consensus: str | None = None


@dataclass
class PolicyEventCalendar:
    """Unified policy and earnings event calendar.

    Attributes:
        generated_at: Calendar generation timestamp.
        start_date: Calendar start date.
        end_date: Calendar end date.
        events: List of scheduled events, sorted chronologically.
        high_impact_count: Number of high-impact events.
    """

    generated_at: datetime
    start_date: datetime
    end_date: datetime
    events: list[CalendarEvent]
    high_impact_count: int


class PolicyEventCalendarBuilder:
    """Build unified policy and earnings event calendar.

    Aggregates events from multiple sources into a single
    chronological calendar with impact classification.
    """

    def __init__(self) -> None:
        logger.info("policy_calendar_builder_initialised")

    def build_calendar(
        self,
        start_date: datetime,
        end_date: datetime,
        custom_events: list[CalendarEvent] | None = None,
    ) -> PolicyEventCalendar:
        """Build calendar for the specified date range.

        Args:
            start_date: Calendar start date.
            end_date: Calendar end date.
            custom_events: Additional custom events to include.

        Returns:
            PolicyEventCalendar with all scheduled events.
        """
        events: list[CalendarEvent] = []

        events.extend(self._get_bi_rate_schedule(start_date, end_date))
        events.extend(self._get_bps_release_schedule(start_date, end_date))
        events.extend(self._get_earnings_season(start_date, end_date))
        events.extend(self._get_bond_auction_schedule(start_date, end_date))

        if custom_events:
            events.extend(custom_events)

        events = [e for e in events if start_date <= e.scheduled_at <= end_date]
        events.sort(key=lambda e: e.scheduled_at)

        high_count = sum(1 for e in events if e.impact == EventImpact.HIGH)

        calendar = PolicyEventCalendar(
            generated_at=datetime.now(timezone.utc),
            start_date=start_date,
            end_date=end_date,
            events=events,
            high_impact_count=high_count,
        )

        logger.info(
            "policy_calendar_built",
            num_events=len(events),
            high_impact=high_count,
        )
        return calendar

    @staticmethod
    def _get_bi_rate_schedule(
        start: datetime, end: datetime
    ) -> list[CalendarEvent]:
        """Generate BI rate decision schedule (3rd-4th week of each month)."""
        events: list[CalendarEvent] = []
        current = start.replace(day=20, hour=7, minute=0, second=0, microsecond=0)

        while current <= end:
            events.append(
                CalendarEvent(
                    event_type=EventType.BI_RATE_DECISION,
                    title=f"BI 7-Day RR Rate Decision — {current.strftime('%B %Y')}",
                    scheduled_at=current,
                    impact=EventImpact.HIGH,
                    affected_assets=["IHSG", "USD/IDR", "SUN", "Banking sector"],
                    description="Bank Indonesia monthly monetary policy meeting (RDG)",
                )
            )
            month = current.month + 1
            year = current.year + (month - 1) // 12
            month = (month - 1) % 12 + 1
            current = current.replace(year=year, month=month)

        return events

    @staticmethod
    def _get_bps_release_schedule(
        start: datetime, end: datetime
    ) -> list[CalendarEvent]:
        """Generate BPS statistical release schedule."""
        events: list[CalendarEvent] = []
        current = start.replace(day=1, hour=3, minute=0, second=0, microsecond=0)

        while current <= end:
            events.append(
                CalendarEvent(
                    event_type=EventType.INFLATION_RELEASE,
                    title=f"BPS CPI Inflation — {current.strftime('%B %Y')}",
                    scheduled_at=current,
                    impact=EventImpact.MEDIUM,
                    affected_assets=["IHSG", "SUN", "Consumer sector"],
                    description="BPS monthly consumer price index release",
                )
            )
            month = current.month + 1
            year = current.year + (month - 1) // 12
            month = (month - 1) % 12 + 1
            current = current.replace(year=year, month=month)

        return events

    @staticmethod
    def _get_earnings_season(
        start: datetime, end: datetime
    ) -> list[CalendarEvent]:
        """Generate IDX earnings season markers (Q1-Q4)."""
        quarters = [
            (1, 31, "Q4 Earnings Season (Annual Reports)"),
            (4, 30, "Q1 Earnings Season"),
            (7, 31, "Q2 Earnings Season (Half-Year)"),
            (10, 31, "Q3 Earnings Season"),
        ]
        events: list[CalendarEvent] = []
        for year in range(start.year, end.year + 1):
            for month, day, title in quarters:
                dt = datetime(year, month, day, tzinfo=timezone.utc)
                if start <= dt <= end:
                    events.append(
                        CalendarEvent(
                            event_type=EventType.EARNINGS_SEASON,
                            title=title,
                            scheduled_at=dt,
                            impact=EventImpact.HIGH,
                            affected_assets=["All IDX equities"],
                            description="Filing deadline for quarterly financial statements",
                        )
                    )
        return events

    @staticmethod
    def _get_bond_auction_schedule(
        start: datetime, end: datetime
    ) -> list[CalendarEvent]:
        """Generate SUN/SBSN bond auction schedule (bi-weekly Tuesday)."""
        events: list[CalendarEvent] = []
        current = start
        while current <= end:
            if current.weekday() == 1 and current.day <= 14:  # First two Tuesdays
                events.append(
                    CalendarEvent(
                        event_type=EventType.BOND_AUCTION,
                        title=f"SUN Bond Auction — {current.strftime('%d %B %Y')}",
                        scheduled_at=current.replace(hour=4, tzinfo=timezone.utc),
                        impact=EventImpact.MEDIUM,
                        affected_assets=["SUN", "SBSN", "Fixed income"],
                        description="Government bond auction (conventional or sukuk)",
                    )
                )
            from datetime import timedelta
            current += timedelta(days=1)

        return events
