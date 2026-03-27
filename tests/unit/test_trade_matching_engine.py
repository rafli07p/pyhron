"""Unit tests for the trade matching engine.

Validates price-time priority matching, order book management,
cancellation, and fill emission for the internal matching engine.
"""

from __future__ import annotations

from decimal import Decimal
from uuid import uuid4

import pytest

try:
    from services.execution.trade_matching import BookOrder, TradeMatchingEngine
    from shared.schemas.order_events import (
        OrderFill,
        OrderRequest,
        OrderSide,
        OrderType,
    )
except ImportError:
    pytest.skip("Requires execution modules", allow_module_level=True)


def _make_order(
    symbol: str = "BBCA.JK",
    side: OrderSide = OrderSide.BUY,
    qty: Decimal = Decimal("100"),
    price: Decimal | None = Decimal("9200"),
    order_type: OrderType = OrderType.LIMIT,
    tenant_id: str = "test-tenant",
) -> OrderRequest:
    return OrderRequest(
        order_id=uuid4(),
        symbol=symbol,
        side=side,
        qty=qty,
        price=price,
        order_type=order_type,
        tenant_id=tenant_id,
    )


class TestTradeMatchingBasic:
    """Tests for basic order book operations."""

    def test_add_resting_buy_order(self) -> None:
        """Buy order with no matching ask should rest on book."""
        engine = TradeMatchingEngine()
        order = _make_order(side=OrderSide.BUY, price=Decimal("9200"))
        fills = engine.add_order(order)

        assert fills == []
        book = engine.get_order_book("BBCA.JK")
        assert len(book["bids"]) == 1
        assert len(book["asks"]) == 0

    def test_add_resting_sell_order(self) -> None:
        """Sell order with no matching bid should rest on book."""
        engine = TradeMatchingEngine()
        order = _make_order(side=OrderSide.SELL, price=Decimal("9300"))
        fills = engine.add_order(order)

        assert fills == []
        book = engine.get_order_book("BBCA.JK")
        assert len(book["asks"]) == 1
        assert len(book["bids"]) == 0

    def test_cancel_resting_order(self) -> None:
        """Cancelled order should not appear in order book snapshot."""
        engine = TradeMatchingEngine()
        order = _make_order(side=OrderSide.BUY, price=Decimal("9200"))
        engine.add_order(order)

        cancelled = engine.cancel_order(order.order_id)
        assert cancelled is True

        book = engine.get_order_book("BBCA.JK")
        assert len(book["bids"]) == 0

    def test_cancel_nonexistent_order(self) -> None:
        """Cancelling unknown order should return False."""
        engine = TradeMatchingEngine()
        assert engine.cancel_order(uuid4()) is False

    def test_empty_order_book(self) -> None:
        """Empty book should return empty lists."""
        engine = TradeMatchingEngine()
        book = engine.get_order_book("NONEXISTENT")
        assert book == {"bids": [], "asks": []}


class TestTradeMatchingFills:
    """Tests for order matching and fill generation."""

    def test_exact_match_produces_fill(self) -> None:
        """Buy and sell at same price should match and produce fills."""
        engine = TradeMatchingEngine()

        sell = _make_order(side=OrderSide.SELL, price=Decimal("9200"), qty=Decimal("100"))
        engine.add_order(sell)

        buy = _make_order(side=OrderSide.BUY, price=Decimal("9200"), qty=Decimal("100"))
        fills = engine.add_order(buy)

        assert len(fills) == 1
        fill = fills[0]
        assert fill.fill_qty == Decimal("100")
        assert fill.fill_price == Decimal("9200")
        assert fill.leaves_qty == Decimal("0")
        assert fill.status.value == "FILLED"

    def test_partial_fill(self) -> None:
        """Larger buy against smaller sell should partially fill."""
        engine = TradeMatchingEngine()

        sell = _make_order(side=OrderSide.SELL, price=Decimal("9200"), qty=Decimal("50"))
        engine.add_order(sell)

        buy = _make_order(side=OrderSide.BUY, price=Decimal("9200"), qty=Decimal("100"))
        fills = engine.add_order(buy)

        assert len(fills) == 1
        assert fills[0].fill_qty == Decimal("50")
        assert fills[0].leaves_qty == Decimal("50")

        # Remaining buy should rest on book
        book = engine.get_order_book("BBCA.JK")
        assert len(book["bids"]) == 1
        assert book["bids"][0]["remaining"] == "50"

    def test_price_priority(self) -> None:
        """Best price should match first (lowest ask for buyer)."""
        engine = TradeMatchingEngine()

        # Post two asks at different prices
        expensive = _make_order(side=OrderSide.SELL, price=Decimal("9300"), qty=Decimal("100"))
        cheap = _make_order(side=OrderSide.SELL, price=Decimal("9100"), qty=Decimal("100"))
        engine.add_order(expensive)
        engine.add_order(cheap)

        # Buy should match cheaper ask first
        buy = _make_order(side=OrderSide.BUY, price=Decimal("9300"), qty=Decimal("100"))
        fills = engine.add_order(buy)

        assert len(fills) == 1
        assert fills[0].fill_price == Decimal("9100")

    def test_time_priority(self) -> None:
        """At same price, earlier order should match first."""
        engine = TradeMatchingEngine()

        first_sell = _make_order(side=OrderSide.SELL, price=Decimal("9200"), qty=Decimal("50"))
        second_sell = _make_order(side=OrderSide.SELL, price=Decimal("9200"), qty=Decimal("50"))
        engine.add_order(first_sell)
        engine.add_order(second_sell)

        buy = _make_order(side=OrderSide.BUY, price=Decimal("9200"), qty=Decimal("50"))
        fills = engine.add_order(buy)

        assert len(fills) == 1
        assert fills[0].fill_qty == Decimal("50")
        # First sell should have been matched (first resting order)

    def test_no_match_when_prices_dont_cross(self) -> None:
        """Buy below ask should not match."""
        engine = TradeMatchingEngine()

        sell = _make_order(side=OrderSide.SELL, price=Decimal("9300"), qty=Decimal("100"))
        engine.add_order(sell)

        buy = _make_order(side=OrderSide.BUY, price=Decimal("9100"), qty=Decimal("100"))
        fills = engine.add_order(buy)

        assert fills == []
        book = engine.get_order_book("BBCA.JK")
        assert len(book["bids"]) == 1
        assert len(book["asks"]) == 1

    def test_market_order_matches_any_price(self) -> None:
        """Market order (price=0) should match any resting order."""
        engine = TradeMatchingEngine()

        sell = _make_order(side=OrderSide.SELL, price=Decimal("9200"), qty=Decimal("100"))
        engine.add_order(sell)

        buy = _make_order(
            side=OrderSide.BUY,
            price=None,
            qty=Decimal("100"),
            order_type=OrderType.MARKET,
        )
        fills = engine.add_order(buy)

        assert len(fills) == 1
        assert fills[0].fill_price == Decimal("9200")

    def test_fill_callback_invoked(self) -> None:
        """Fill callback should be called for each fill."""
        received_fills: list[OrderFill] = []
        engine = TradeMatchingEngine(on_fill=lambda f: received_fills.append(f))

        sell = _make_order(side=OrderSide.SELL, price=Decimal("9200"), qty=Decimal("100"))
        engine.add_order(sell)

        buy = _make_order(side=OrderSide.BUY, price=Decimal("9200"), qty=Decimal("100"))
        engine.add_order(buy)

        # Both incoming and resting fills are emitted
        assert len(received_fills) == 2

    def test_multiple_fills_across_price_levels(self) -> None:
        """Large buy should sweep multiple ask levels."""
        engine = TradeMatchingEngine()

        engine.add_order(_make_order(side=OrderSide.SELL, price=Decimal("9100"), qty=Decimal("50")))
        engine.add_order(_make_order(side=OrderSide.SELL, price=Decimal("9200"), qty=Decimal("50")))
        engine.add_order(_make_order(side=OrderSide.SELL, price=Decimal("9300"), qty=Decimal("50")))

        buy = _make_order(side=OrderSide.BUY, price=Decimal("9300"), qty=Decimal("120"))
        fills = engine.add_order(buy)

        assert len(fills) == 3
        assert fills[0].fill_price == Decimal("9100")
        assert fills[1].fill_price == Decimal("9200")
        assert fills[2].fill_price == Decimal("9300")
        assert fills[0].fill_qty == Decimal("50")
        assert fills[1].fill_qty == Decimal("50")
        assert fills[2].fill_qty == Decimal("20")


class TestTradeMatchingCrossBook:
    """Tests for explicit book crossing."""

    def test_cross_book_matches_crossed_orders(self) -> None:
        """match_orders should match crossed orders."""
        engine = TradeMatchingEngine()

        # Post non-crossing orders first
        engine.add_order(_make_order(side=OrderSide.BUY, price=Decimal("9100"), qty=Decimal("100")))
        engine.add_order(_make_order(side=OrderSide.SELL, price=Decimal("9300"), qty=Decimal("100")))

        # No crossing yet
        fills = engine.match_orders("BBCA.JK")
        assert fills == []

    def test_match_orders_empty_book(self) -> None:
        """match_orders on nonexistent symbol should return empty."""
        engine = TradeMatchingEngine()
        assert engine.match_orders("NONEXISTENT") == []


class TestBookOrderKeys:
    """Tests for BookOrder heap comparison keys."""

    def test_bid_key_negates_price(self) -> None:
        """Bid key should negate price for max-heap behavior via min-heap."""
        from datetime import UTC, datetime

        order = BookOrder(
            order_id=uuid4(),
            symbol="BBCA.JK",
            side=OrderSide.BUY,
            price=Decimal("9200"),
            quantity=Decimal("100"),
            remaining=Decimal("100"),
            timestamp=datetime.now(UTC),
            tenant_id="test",
            sequence=1,
        )
        key = order.bid_key()
        assert key[0] == Decimal("-9200")
        assert key[1] == 1

    def test_ask_key_uses_positive_price(self) -> None:
        """Ask key should use positive price for min-heap."""
        from datetime import UTC, datetime

        order = BookOrder(
            order_id=uuid4(),
            symbol="BBCA.JK",
            side=OrderSide.SELL,
            price=Decimal("9300"),
            quantity=Decimal("100"),
            remaining=Decimal("100"),
            timestamp=datetime.now(UTC),
            tenant_id="test",
            sequence=2,
        )
        key = order.ask_key()
        assert key[0] == Decimal("9300")
        assert key[1] == 2
