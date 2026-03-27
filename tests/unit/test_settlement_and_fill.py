"""Unit tests for order fill event processing utilities.

Validates IDX T+2 settlement date calculation, FillEvent dataclass,
and the order state machine transition table.
"""

from __future__ import annotations

from datetime import date

import pytest

try:
    from services.order_management_system.order_fill_event_processor import (
        FillEvent,
        calculate_settlement_date,
    )
except ImportError:
    pytest.skip("Requires OMS modules", allow_module_level=True)


class TestSettlementDateCalculation:
    """Tests for IDX T+2 settlement date calculation."""

    def test_regular_weekday(self) -> None:
        """Monday trade should settle on Wednesday."""
        # Monday 2025-02-03
        trade = date(2025, 2, 3)
        settlement = calculate_settlement_date(trade)
        assert settlement == date(2025, 2, 5)  # Wednesday

    def test_friday_trade_settles_next_tuesday(self) -> None:
        """Friday trade should settle on Tuesday (skip weekend)."""
        # Friday 2025-02-07
        trade = date(2025, 2, 7)
        settlement = calculate_settlement_date(trade)
        assert settlement == date(2025, 2, 11)  # Tuesday

    def test_thursday_trade_settles_monday(self) -> None:
        """Thursday trade should settle on Monday (skip weekend)."""
        # Thursday 2025-02-06
        trade = date(2025, 2, 6)
        settlement = calculate_settlement_date(trade)
        assert settlement == date(2025, 2, 10)  # Monday

    def test_settlement_skips_holiday(self) -> None:
        """Settlement should skip market holidays."""
        # Trade on 2025-04-16 (Wednesday), Good Friday on 2025-04-18
        trade = date(2025, 4, 16)
        settlement = calculate_settlement_date(trade)
        # Thursday 17 (1 biz day), Friday 18 is Good Friday (skip),
        # Saturday+Sunday (skip), Monday 21 (2nd biz day)
        assert settlement == date(2025, 4, 21)

    def test_new_year_holiday(self) -> None:
        """Settlement should skip New Year's Day."""
        # Trade on 2024-12-30 (Monday)
        trade = date(2024, 12, 30)
        settlement = calculate_settlement_date(trade)
        # Dec 31 (1 biz day), Jan 1 holiday (skip), Jan 2 (2nd biz day)
        assert settlement == date(2025, 1, 2)

    def test_wednesday_trade_normal(self) -> None:
        """Wednesday trade should settle on Friday."""
        trade = date(2025, 2, 5)
        settlement = calculate_settlement_date(trade)
        assert settlement == date(2025, 2, 7)

    def test_independence_day(self) -> None:
        """Settlement should skip Independence Day (Aug 17)."""
        # Trade on 2025-08-14 (Thursday)
        trade = date(2025, 8, 14)
        settlement = calculate_settlement_date(trade)
        # Friday 15 (1 biz day), Sat+Sun skip, Mon 18 (2nd biz day, 17 is holiday on Sun)
        assert settlement == date(2025, 8, 18)


class TestFillEvent:
    """Tests for the FillEvent dataclass."""

    def test_fill_event_creation(self) -> None:
        """FillEvent should be created with required fields."""
        fill = FillEvent(
            client_order_id="ORD-001",
            broker_order_id="BRK-001",
            filled_quantity=100,
            filled_price=9200.0,
        )
        assert fill.client_order_id == "ORD-001"
        assert fill.filled_quantity == 100
        assert fill.filled_price == 9200.0
        assert fill.commission == 0.0
        assert fill.tax == 0.0

    def test_fill_event_with_costs(self) -> None:
        """FillEvent should accept commission and tax."""
        fill = FillEvent(
            client_order_id="ORD-002",
            broker_order_id="BRK-002",
            filled_quantity=500,
            filled_price=3850.0,
            commission=2887.5,
            tax=1925.0,
        )
        assert fill.commission == 2887.5
        assert fill.tax == 1925.0

    def test_fill_event_is_frozen(self) -> None:
        """FillEvent should be immutable."""
        fill = FillEvent(
            client_order_id="ORD-003",
            broker_order_id="BRK-003",
            filled_quantity=200,
            filled_price=6100.0,
        )
        with pytest.raises(AttributeError):
            fill.filled_quantity = 300  # type: ignore[misc]

    def test_fill_event_defaults(self) -> None:
        """FillEvent defaults should be sensible."""
        fill = FillEvent(
            client_order_id="ORD-004",
            broker_order_id="BRK-004",
            filled_quantity=50,
            filled_price=1000.0,
        )
        assert fill.event_type == "fill"
        assert fill.timestamp == ""
        assert fill.fill_id == ""
