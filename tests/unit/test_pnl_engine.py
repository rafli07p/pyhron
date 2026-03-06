"""
Tests for the PnL (Profit and Loss) calculation engine.

Validates realized PnL, unrealized PnL, daily aggregation,
fee handling, and multi-currency support.
"""

from __future__ import annotations

from datetime import date, datetime, timezone, timedelta
from decimal import Decimal
from uuid import uuid4

import pytest

from enthropy.pnl.engine import PnLEngine
from enthropy.pnl.models import (
    FillRecord,
    PnLReport,
    PnLSummary,
    TradeDirection,
)


# =============================================================================
# Fixtures
# =============================================================================
@pytest.fixture
def pnl_engine() -> PnLEngine:
    """Fresh PnL engine instance."""
    return PnLEngine()


@pytest.fixture
def sample_fills() -> list[FillRecord]:
    """Sample fill records for a round-trip trade."""
    now = datetime.now(timezone.utc)
    return [
        FillRecord(
            fill_id=uuid4(),
            order_id=uuid4(),
            symbol="BBCA.JK",
            direction=TradeDirection.BUY,
            quantity=Decimal("1000"),
            price=Decimal("9200.00"),
            commission=Decimal("13800.00"),  # 0.15% of notional
            timestamp=now - timedelta(hours=2),
            strategy_id="momentum_v1",
        ),
        FillRecord(
            fill_id=uuid4(),
            order_id=uuid4(),
            symbol="BBCA.JK",
            direction=TradeDirection.SELL,
            quantity=Decimal("1000"),
            price=Decimal("9350.00"),
            commission=Decimal("14025.00"),  # 0.15% of notional
            timestamp=now,
            strategy_id="momentum_v1",
        ),
    ]


# =============================================================================
# Realized PnL Tests
# =============================================================================
class TestRealizedPnL:
    """Tests for realized PnL calculations."""

    def test_profitable_round_trip(self, pnl_engine: PnLEngine, sample_fills: list[FillRecord]):
        """Profitable round-trip trade should have positive realized PnL."""
        for fill in sample_fills:
            pnl_engine.process_fill(fill)

        pnl = pnl_engine.get_realized_pnl("BBCA.JK")
        # Gross PnL: (9350 - 9200) * 1000 = 150,000
        # Net PnL: 150,000 - 13,800 - 14,025 = 122,175
        assert pnl.gross_pnl == Decimal("150000.00")
        assert pnl.total_commissions == Decimal("27825.00")
        assert pnl.net_pnl == Decimal("122175.00")

    def test_losing_round_trip(self, pnl_engine: PnLEngine):
        """Losing round-trip trade should have negative realized PnL."""
        now = datetime.now(timezone.utc)
        buy_fill = FillRecord(
            fill_id=uuid4(),
            order_id=uuid4(),
            symbol="TLKM.JK",
            direction=TradeDirection.BUY,
            quantity=Decimal("2000"),
            price=Decimal("3900.00"),
            commission=Decimal("11700.00"),
            timestamp=now - timedelta(hours=1),
            strategy_id="value_v1",
        )
        sell_fill = FillRecord(
            fill_id=uuid4(),
            order_id=uuid4(),
            symbol="TLKM.JK",
            direction=TradeDirection.SELL,
            quantity=Decimal("2000"),
            price=Decimal("3800.00"),
            commission=Decimal("11400.00"),
            timestamp=now,
            strategy_id="value_v1",
        )
        pnl_engine.process_fill(buy_fill)
        pnl_engine.process_fill(sell_fill)

        pnl = pnl_engine.get_realized_pnl("TLKM.JK")
        # Gross PnL: (3800 - 3900) * 2000 = -200,000
        assert pnl.gross_pnl == Decimal("-200000.00")
        assert pnl.net_pnl < pnl.gross_pnl  # Net is worse after commissions

    def test_short_trade_profit(self, pnl_engine: PnLEngine):
        """Profitable short trade should have positive realized PnL."""
        now = datetime.now(timezone.utc)
        sell_fill = FillRecord(
            fill_id=uuid4(),
            order_id=uuid4(),
            symbol="BMRI.JK",
            direction=TradeDirection.SELL,
            quantity=Decimal("500"),
            price=Decimal("6200.00"),
            commission=Decimal("4650.00"),
            timestamp=now - timedelta(hours=1),
            strategy_id="stat_arb_v1",
        )
        buy_fill = FillRecord(
            fill_id=uuid4(),
            order_id=uuid4(),
            symbol="BMRI.JK",
            direction=TradeDirection.BUY,
            quantity=Decimal("500"),
            price=Decimal("6050.00"),
            commission=Decimal("4537.50"),
            timestamp=now,
            strategy_id="stat_arb_v1",
        )
        pnl_engine.process_fill(sell_fill)
        pnl_engine.process_fill(buy_fill)

        pnl = pnl_engine.get_realized_pnl("BMRI.JK")
        # Gross PnL: (6200 - 6050) * 500 = 75,000
        assert pnl.gross_pnl == Decimal("75000.00")
        assert pnl.net_pnl > 0

    def test_partial_close_pnl(self, pnl_engine: PnLEngine):
        """Partial position close should calculate PnL correctly."""
        now = datetime.now(timezone.utc)
        # Buy 1000 shares
        pnl_engine.process_fill(FillRecord(
            fill_id=uuid4(),
            order_id=uuid4(),
            symbol="BBCA.JK",
            direction=TradeDirection.BUY,
            quantity=Decimal("1000"),
            price=Decimal("9200.00"),
            commission=Decimal("13800.00"),
            timestamp=now - timedelta(hours=2),
            strategy_id="momentum_v1",
        ))
        # Sell 600 shares (partial)
        pnl_engine.process_fill(FillRecord(
            fill_id=uuid4(),
            order_id=uuid4(),
            symbol="BBCA.JK",
            direction=TradeDirection.SELL,
            quantity=Decimal("600"),
            price=Decimal("9400.00"),
            commission=Decimal("8460.00"),
            timestamp=now,
            strategy_id="momentum_v1",
        ))

        pnl = pnl_engine.get_realized_pnl("BBCA.JK")
        # Gross PnL on 600 shares: (9400 - 9200) * 600 = 120,000
        assert pnl.gross_pnl == Decimal("120000.00")
        # Remaining position: 400 shares (unrealized)
        remaining = pnl_engine.get_open_quantity("BBCA.JK")
        assert remaining == Decimal("400")


# =============================================================================
# Unrealized PnL Tests
# =============================================================================
class TestUnrealizedPnL:
    """Tests for unrealized PnL calculations."""

    def test_unrealized_pnl_long(self, pnl_engine: PnLEngine):
        """Unrealized PnL for long position with price increase."""
        now = datetime.now(timezone.utc)
        pnl_engine.process_fill(FillRecord(
            fill_id=uuid4(),
            order_id=uuid4(),
            symbol="BBCA.JK",
            direction=TradeDirection.BUY,
            quantity=Decimal("1000"),
            price=Decimal("9200.00"),
            commission=Decimal("13800.00"),
            timestamp=now,
            strategy_id="momentum_v1",
        ))

        unrealized = pnl_engine.calculate_unrealized_pnl(
            symbol="BBCA.JK",
            current_price=Decimal("9500.00"),
        )
        # (9500 - 9200) * 1000 = 300,000
        assert unrealized == Decimal("300000.00")

    def test_unrealized_pnl_short(self, pnl_engine: PnLEngine):
        """Unrealized PnL for short position with price decrease."""
        now = datetime.now(timezone.utc)
        pnl_engine.process_fill(FillRecord(
            fill_id=uuid4(),
            order_id=uuid4(),
            symbol="TLKM.JK",
            direction=TradeDirection.SELL,
            quantity=Decimal("2000"),
            price=Decimal("3900.00"),
            commission=Decimal("11700.00"),
            timestamp=now,
            strategy_id="pairs_v1",
        ))

        unrealized = pnl_engine.calculate_unrealized_pnl(
            symbol="TLKM.JK",
            current_price=Decimal("3800.00"),
        )
        # Short profit: (3900 - 3800) * 2000 = 200,000
        assert unrealized == Decimal("200000.00")

    def test_unrealized_loss(self, pnl_engine: PnLEngine):
        """Unrealized loss should be negative."""
        now = datetime.now(timezone.utc)
        pnl_engine.process_fill(FillRecord(
            fill_id=uuid4(),
            order_id=uuid4(),
            symbol="BBCA.JK",
            direction=TradeDirection.BUY,
            quantity=Decimal("1000"),
            price=Decimal("9200.00"),
            commission=Decimal("13800.00"),
            timestamp=now,
            strategy_id="momentum_v1",
        ))

        unrealized = pnl_engine.calculate_unrealized_pnl(
            symbol="BBCA.JK",
            current_price=Decimal("9000.00"),
        )
        # (9000 - 9200) * 1000 = -200,000
        assert unrealized == Decimal("-200000.00")

    def test_no_position_returns_zero(self, pnl_engine: PnLEngine):
        """Unrealized PnL for non-existent position should be zero."""
        unrealized = pnl_engine.calculate_unrealized_pnl(
            symbol="NONEXISTENT",
            current_price=Decimal("100.00"),
        )
        assert unrealized == Decimal("0")


# =============================================================================
# Daily PnL Aggregation Tests
# =============================================================================
class TestDailyPnLAggregation:
    """Tests for daily PnL report generation."""

    def test_daily_pnl_report(self, pnl_engine: PnLEngine, sample_fills: list[FillRecord]):
        """Daily PnL report should aggregate fills correctly."""
        for fill in sample_fills:
            pnl_engine.process_fill(fill)

        report = pnl_engine.generate_daily_report(
            report_date=date.today(),
            current_prices={"BBCA.JK": Decimal("9350.00")},
        )
        assert isinstance(report, PnLReport)
        assert report.report_date == date.today()
        assert report.total_realized_pnl is not None

    def test_multi_symbol_daily_report(self, pnl_engine: PnLEngine):
        """Daily report with multiple symbols should aggregate correctly."""
        now = datetime.now(timezone.utc)

        symbols_data = [
            ("BBCA.JK", Decimal("9200"), Decimal("9350"), Decimal("1000")),
            ("TLKM.JK", Decimal("3800"), Decimal("3750"), Decimal("2000")),
            ("BMRI.JK", Decimal("6100"), Decimal("6200"), Decimal("500")),
        ]

        for symbol, buy_price, sell_price, qty in symbols_data:
            pnl_engine.process_fill(FillRecord(
                fill_id=uuid4(),
                order_id=uuid4(),
                symbol=symbol,
                direction=TradeDirection.BUY,
                quantity=qty,
                price=buy_price,
                commission=buy_price * qty * Decimal("0.0015"),
                timestamp=now - timedelta(hours=2),
                strategy_id="multi_v1",
            ))
            pnl_engine.process_fill(FillRecord(
                fill_id=uuid4(),
                order_id=uuid4(),
                symbol=symbol,
                direction=TradeDirection.SELL,
                quantity=qty,
                price=sell_price,
                commission=sell_price * qty * Decimal("0.0015"),
                timestamp=now,
                strategy_id="multi_v1",
            ))

        report = pnl_engine.generate_daily_report(
            report_date=date.today(),
            current_prices={
                "BBCA.JK": Decimal("9350"),
                "TLKM.JK": Decimal("3750"),
                "BMRI.JK": Decimal("6200"),
            },
        )
        assert len(report.by_symbol) == 3

    def test_pnl_summary_statistics(self, pnl_engine: PnLEngine):
        """PnL summary should include key statistics."""
        now = datetime.now(timezone.utc)

        # Create a series of trades over multiple days
        for day_offset in range(5):
            trade_time = now - timedelta(days=day_offset)
            buy_price = Decimal("9000") + Decimal(str(day_offset * 50))
            sell_price = buy_price + Decimal("100")

            pnl_engine.process_fill(FillRecord(
                fill_id=uuid4(),
                order_id=uuid4(),
                symbol="BBCA.JK",
                direction=TradeDirection.BUY,
                quantity=Decimal("100"),
                price=buy_price,
                commission=Decimal("1350"),
                timestamp=trade_time - timedelta(hours=1),
                strategy_id="test_v1",
            ))
            pnl_engine.process_fill(FillRecord(
                fill_id=uuid4(),
                order_id=uuid4(),
                symbol="BBCA.JK",
                direction=TradeDirection.SELL,
                quantity=Decimal("100"),
                price=sell_price,
                commission=Decimal("1365"),
                timestamp=trade_time,
                strategy_id="test_v1",
            ))

        summary = pnl_engine.get_summary(strategy_id="test_v1")
        assert isinstance(summary, PnLSummary)
        assert summary.total_trades == 5
        assert summary.win_rate > 0
        assert summary.total_net_pnl > 0


# =============================================================================
# Fee and Commission Tests
# =============================================================================
class TestFeeHandling:
    """Tests for commission and fee calculations."""

    def test_commission_deducted_from_pnl(self, pnl_engine: PnLEngine):
        """Commissions should reduce net PnL."""
        now = datetime.now(timezone.utc)
        pnl_engine.process_fill(FillRecord(
            fill_id=uuid4(),
            order_id=uuid4(),
            symbol="BBCA.JK",
            direction=TradeDirection.BUY,
            quantity=Decimal("1000"),
            price=Decimal("9200.00"),
            commission=Decimal("50000.00"),  # High commission
            timestamp=now - timedelta(hours=1),
            strategy_id="test_v1",
        ))
        pnl_engine.process_fill(FillRecord(
            fill_id=uuid4(),
            order_id=uuid4(),
            symbol="BBCA.JK",
            direction=TradeDirection.SELL,
            quantity=Decimal("1000"),
            price=Decimal("9250.00"),
            commission=Decimal("50000.00"),
            timestamp=now,
            strategy_id="test_v1",
        ))

        pnl = pnl_engine.get_realized_pnl("BBCA.JK")
        # Gross: 50,000, Commissions: 100,000, Net: -50,000
        assert pnl.gross_pnl == Decimal("50000.00")
        assert pnl.net_pnl == Decimal("-50000.00")

    def test_zero_commission(self, pnl_engine: PnLEngine):
        """Zero commission trades should have gross == net PnL."""
        now = datetime.now(timezone.utc)
        pnl_engine.process_fill(FillRecord(
            fill_id=uuid4(),
            order_id=uuid4(),
            symbol="BBCA.JK",
            direction=TradeDirection.BUY,
            quantity=Decimal("100"),
            price=Decimal("9200.00"),
            commission=Decimal("0"),
            timestamp=now - timedelta(hours=1),
            strategy_id="test_v1",
        ))
        pnl_engine.process_fill(FillRecord(
            fill_id=uuid4(),
            order_id=uuid4(),
            symbol="BBCA.JK",
            direction=TradeDirection.SELL,
            quantity=Decimal("100"),
            price=Decimal("9300.00"),
            commission=Decimal("0"),
            timestamp=now,
            strategy_id="test_v1",
        ))

        pnl = pnl_engine.get_realized_pnl("BBCA.JK")
        assert pnl.gross_pnl == pnl.net_pnl


# =============================================================================
# Edge Case Tests
# =============================================================================
class TestEdgeCases:
    """Tests for edge cases and boundary conditions."""

    def test_fractional_quantities(self, pnl_engine: PnLEngine):
        """Fractional share quantities should be handled correctly."""
        now = datetime.now(timezone.utc)
        pnl_engine.process_fill(FillRecord(
            fill_id=uuid4(),
            order_id=uuid4(),
            symbol="BTC-USD",
            direction=TradeDirection.BUY,
            quantity=Decimal("0.5"),
            price=Decimal("43000.00"),
            commission=Decimal("21.50"),
            timestamp=now - timedelta(hours=1),
            strategy_id="crypto_v1",
        ))
        pnl_engine.process_fill(FillRecord(
            fill_id=uuid4(),
            order_id=uuid4(),
            symbol="BTC-USD",
            direction=TradeDirection.SELL,
            quantity=Decimal("0.5"),
            price=Decimal("44000.00"),
            commission=Decimal("22.00"),
            timestamp=now,
            strategy_id="crypto_v1",
        ))

        pnl = pnl_engine.get_realized_pnl("BTC-USD")
        # Gross: (44000 - 43000) * 0.5 = 500
        assert pnl.gross_pnl == Decimal("500.00")

    def test_very_small_price_differences(self, pnl_engine: PnLEngine):
        """Very small price differences should be tracked precisely."""
        now = datetime.now(timezone.utc)
        pnl_engine.process_fill(FillRecord(
            fill_id=uuid4(),
            order_id=uuid4(),
            symbol="USDIDR",
            direction=TradeDirection.BUY,
            quantity=Decimal("1000000"),
            price=Decimal("15450.50"),
            commission=Decimal("1000.00"),
            timestamp=now - timedelta(hours=1),
            strategy_id="fx_v1",
        ))
        pnl_engine.process_fill(FillRecord(
            fill_id=uuid4(),
            order_id=uuid4(),
            symbol="USDIDR",
            direction=TradeDirection.SELL,
            quantity=Decimal("1000000"),
            price=Decimal("15451.00"),
            commission=Decimal("1000.00"),
            timestamp=now,
            strategy_id="fx_v1",
        ))

        pnl = pnl_engine.get_realized_pnl("USDIDR")
        # Gross: 0.50 * 1,000,000 = 500,000
        assert pnl.gross_pnl == Decimal("500000.00")

    def test_duplicate_fill_rejected(self, pnl_engine: PnLEngine):
        """Duplicate fill IDs should be rejected."""
        fill_id = uuid4()
        now = datetime.now(timezone.utc)
        fill = FillRecord(
            fill_id=fill_id,
            order_id=uuid4(),
            symbol="BBCA.JK",
            direction=TradeDirection.BUY,
            quantity=Decimal("100"),
            price=Decimal("9200.00"),
            commission=Decimal("1380.00"),
            timestamp=now,
            strategy_id="test_v1",
        )
        pnl_engine.process_fill(fill)

        with pytest.raises(ValueError, match="[Dd]uplicate"):
            pnl_engine.process_fill(fill)
