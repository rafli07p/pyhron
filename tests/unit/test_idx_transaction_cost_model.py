"""Unit tests for IDX transaction cost model.

Tests:
  - Buy commission: 0.15% of transaction value
  - Sell commission: 0.25% (0.15% broker + 0.1% sales tax)
  - Lot size rounding: IDX requires multiples of 100 shares
  - T+2 settlement date calculation
"""

from __future__ import annotations

from datetime import date, timedelta

import pytest

# ── IDX Cost Model (pure functions under test) ──────────────────────────────


def compute_buy_commission(quantity: int, price: float, rate: float = 0.0015) -> float:
    """Compute buy-side commission for IDX equities."""
    return quantity * price * rate


def compute_sell_commission(
    quantity: int,
    price: float,
    broker_rate: float = 0.0015,
    tax_rate: float = 0.001,
) -> float:
    """Compute sell-side commission for IDX equities (includes sales tax)."""
    value = quantity * price
    return value * (broker_rate + tax_rate)


def round_to_lot(quantity: int, lot_size: int = 100) -> int:
    """Round quantity down to nearest lot."""
    return (quantity // lot_size) * lot_size


def compute_settlement_date(trade_date: date) -> date:
    """Compute T+2 settlement date, skipping weekends."""
    days_added = 0
    current = trade_date
    while days_added < 2:
        current += timedelta(days=1)
        if current.weekday() < 5:  # Monday=0, Friday=4
            days_added += 1
    return current


# ── Buy Commission Tests ────────────────────────────────────────────────────


class TestBuyCommission:
    def test_standard_buy(self):
        commission = compute_buy_commission(1000, 9200.0)
        assert commission == pytest.approx(13_800.0)  # 1000 * 9200 * 0.0015

    def test_single_lot_buy(self):
        commission = compute_buy_commission(100, 9200.0)
        assert commission == pytest.approx(1_380.0)

    def test_buy_rate_is_015_percent(self):
        value = 100 * 10_000.0
        commission = compute_buy_commission(100, 10_000.0)
        assert commission == pytest.approx(value * 0.0015)

    def test_zero_quantity_buy(self):
        assert compute_buy_commission(0, 9200.0) == 0.0


# ── Sell Commission Tests ───────────────────────────────────────────────────


class TestSellCommission:
    def test_standard_sell(self):
        commission = compute_sell_commission(1000, 9200.0)
        # 1000 * 9200 * (0.0015 + 0.001) = 9_200_000 * 0.0025 = 23_000
        assert commission == pytest.approx(23_000.0)

    def test_sell_includes_tax(self):
        broker_only = compute_buy_commission(1000, 9200.0)
        sell_total = compute_sell_commission(1000, 9200.0)
        tax_portion = 1000 * 9200.0 * 0.001
        assert sell_total == pytest.approx(broker_only + tax_portion)

    def test_sell_rate_is_025_percent(self):
        value = 100 * 5000.0
        commission = compute_sell_commission(100, 5000.0)
        assert commission == pytest.approx(value * 0.0025)

    def test_zero_quantity_sell(self):
        assert compute_sell_commission(0, 9200.0) == 0.0


# ── Lot Size Rounding Tests ─────────────────────────────────────────────────


class TestLotSizeRounding:
    def test_exact_lot(self):
        assert round_to_lot(500) == 500

    def test_round_down(self):
        assert round_to_lot(350) == 300

    def test_sub_lot_rounds_to_zero(self):
        assert round_to_lot(50) == 0

    def test_single_lot(self):
        assert round_to_lot(100) == 100

    def test_large_quantity(self):
        assert round_to_lot(12_345) == 12_300


# ── T+2 Settlement Date Tests ──────────────────────────────────────────────


class TestSettlementDate:
    def test_monday_settles_wednesday(self):
        assert compute_settlement_date(date(2025, 1, 6)) == date(2025, 1, 8)

    def test_wednesday_settles_friday(self):
        assert compute_settlement_date(date(2025, 1, 8)) == date(2025, 1, 10)

    def test_thursday_settles_monday(self):
        assert compute_settlement_date(date(2025, 1, 9)) == date(2025, 1, 13)

    def test_friday_settles_tuesday(self):
        assert compute_settlement_date(date(2025, 1, 10)) == date(2025, 1, 14)

    def test_saturday_trade_settles_tuesday(self):
        # Edge case: if somehow traded on Saturday
        assert compute_settlement_date(date(2025, 1, 11)) == date(2025, 1, 14)
