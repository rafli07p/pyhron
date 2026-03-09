"""
Tests for shared Pydantic schemas.

Validates serialization, deserialization, and constraint enforcement
for all domain schemas used across the Enthropy platform.
"""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from uuid import uuid4

import pytest
from enthropy.shared.schemas.order import (
    OrderCreate,
    OrderResponse,
    OrderSide,
    OrderStatus,
    OrderType,
)
from enthropy.shared.schemas.position import PositionSnapshot
from enthropy.shared.schemas.risk import RiskLimits
from enthropy.shared.schemas.tick import TickData
from pydantic import ValidationError


# =============================================================================
# OrderCreate Schema Tests
# =============================================================================
class TestOrderCreateSchema:
    """Tests for the OrderCreate schema."""

    @pytest.mark.parametrize(
        "side,order_type,quantity,price",
        [
            (OrderSide.BUY, OrderType.MARKET, Decimal("100"), None),
            (OrderSide.SELL, OrderType.MARKET, Decimal("50.5"), None),
            (OrderSide.BUY, OrderType.LIMIT, Decimal("10"), Decimal("150.25")),
            (OrderSide.SELL, OrderType.LIMIT, Decimal("1000"), Decimal("0.01")),
            (OrderSide.BUY, OrderType.STOP, Decimal("200"), Decimal("99.99")),
            (OrderSide.SELL, OrderType.STOP_LIMIT, Decimal("75"), Decimal("50.00")),
        ],
    )
    def test_valid_order_creation(
        self, side: OrderSide, order_type: OrderType, quantity: Decimal, price: Decimal | None
    ):
        """Valid orders should be created without errors."""
        order = OrderCreate(
            symbol="BBCA.JK",
            side=side,
            order_type=order_type,
            quantity=quantity,
            price=price,
            strategy_id="mean_reversion_v1",
        )
        assert order.symbol == "BBCA.JK"
        assert order.side == side
        assert order.order_type == order_type
        assert order.quantity == quantity

    @pytest.mark.parametrize(
        "invalid_data,expected_error",
        [
            # Missing required fields
            (
                {"symbol": "BBCA.JK"},
                "side",
            ),
            # Negative quantity
            (
                {
                    "symbol": "BBCA.JK",
                    "side": "buy",
                    "order_type": "market",
                    "quantity": Decimal("-10"),
                    "strategy_id": "test",
                },
                "quantity",
            ),
            # Zero quantity
            (
                {
                    "symbol": "BBCA.JK",
                    "side": "buy",
                    "order_type": "market",
                    "quantity": Decimal("0"),
                    "strategy_id": "test",
                },
                "quantity",
            ),
            # Limit order without price
            (
                {
                    "symbol": "BBCA.JK",
                    "side": "buy",
                    "order_type": "limit",
                    "quantity": Decimal("10"),
                    "price": None,
                    "strategy_id": "test",
                },
                "price",
            ),
            # Empty symbol
            (
                {
                    "symbol": "",
                    "side": "buy",
                    "order_type": "market",
                    "quantity": Decimal("10"),
                    "strategy_id": "test",
                },
                "symbol",
            ),
            # Invalid side
            (
                {
                    "symbol": "BBCA.JK",
                    "side": "hold",
                    "order_type": "market",
                    "quantity": Decimal("10"),
                    "strategy_id": "test",
                },
                "side",
            ),
        ],
    )
    def test_invalid_order_rejected(self, invalid_data: dict, expected_error: str):
        """Invalid orders should raise ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            OrderCreate(**invalid_data)
        assert expected_error.lower() in str(exc_info.value).lower()

    def test_order_serialization_roundtrip(self):
        """Order should survive JSON serialization/deserialization."""
        order = OrderCreate(
            symbol="TLKM.JK",
            side=OrderSide.BUY,
            order_type=OrderType.LIMIT,
            quantity=Decimal("500"),
            price=Decimal("3850.00"),
            strategy_id="momentum_v2",
        )
        json_str = order.model_dump_json()
        restored = OrderCreate.model_validate_json(json_str)
        assert restored.symbol == order.symbol
        assert restored.quantity == order.quantity
        assert restored.price == order.price


# =============================================================================
# OrderResponse Schema Tests
# =============================================================================
class TestOrderResponseSchema:
    """Tests for the OrderResponse schema."""

    def test_valid_response(self):
        """Valid order response should include all fields."""
        order_id = uuid4()
        response = OrderResponse(
            order_id=order_id,
            symbol="BBRI.JK",
            side=OrderSide.BUY,
            order_type=OrderType.MARKET,
            quantity=Decimal("100"),
            filled_quantity=Decimal("100"),
            price=None,
            average_fill_price=Decimal("4525.00"),
            status=OrderStatus.FILLED,
            strategy_id="pairs_trading_v1",
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )
        assert response.order_id == order_id
        assert response.status == OrderStatus.FILLED
        assert response.filled_quantity == Decimal("100")

    def test_partial_fill(self):
        """Partially filled order should have correct quantities."""
        response = OrderResponse(
            order_id=uuid4(),
            symbol="BMRI.JK",
            side=OrderSide.SELL,
            order_type=OrderType.LIMIT,
            quantity=Decimal("1000"),
            filled_quantity=Decimal("750"),
            price=Decimal("6200.00"),
            average_fill_price=Decimal("6205.50"),
            status=OrderStatus.PARTIALLY_FILLED,
            strategy_id="stat_arb_v1",
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )
        assert response.filled_quantity < response.quantity
        assert response.status == OrderStatus.PARTIALLY_FILLED


# =============================================================================
# TickData Schema Tests
# =============================================================================
class TestTickDataSchema:
    """Tests for the TickData schema."""

    @pytest.mark.parametrize(
        "symbol,price,volume",
        [
            ("BBCA.JK", Decimal("9250.00"), 1_500_000),
            ("AAPL", Decimal("185.50"), 50_000_000),
            ("BTC-USD", Decimal("43250.75"), 25_000),
            ("USDIDR", Decimal("15450.50"), 100_000),
        ],
    )
    def test_valid_tick_data(self, symbol: str, price: Decimal, volume: int):
        """Valid tick data should be created successfully."""
        tick = TickData(
            symbol=symbol,
            price=price,
            volume=volume,
            bid=price - Decimal("0.50"),
            ask=price + Decimal("0.50"),
            timestamp=datetime.now(UTC),
            exchange="IDX",
        )
        assert tick.symbol == symbol
        assert tick.price == price
        assert tick.spread == Decimal("1.00")

    @pytest.mark.parametrize(
        "invalid_data",
        [
            # Negative price
            {
                "symbol": "BBCA.JK",
                "price": Decimal("-100"),
                "volume": 1000,
                "bid": Decimal("99"),
                "ask": Decimal("101"),
                "timestamp": datetime.now(UTC),
                "exchange": "IDX",
            },
            # Negative volume
            {
                "symbol": "BBCA.JK",
                "price": Decimal("100"),
                "volume": -1000,
                "bid": Decimal("99"),
                "ask": Decimal("101"),
                "timestamp": datetime.now(UTC),
                "exchange": "IDX",
            },
            # Bid > Ask (crossed market)
            {
                "symbol": "BBCA.JK",
                "price": Decimal("100"),
                "volume": 1000,
                "bid": Decimal("102"),
                "ask": Decimal("99"),
                "timestamp": datetime.now(UTC),
                "exchange": "IDX",
            },
        ],
    )
    def test_invalid_tick_data_rejected(self, invalid_data: dict):
        """Invalid tick data should raise ValidationError."""
        with pytest.raises(ValidationError):
            TickData(**invalid_data)


# =============================================================================
# PositionSnapshot Schema Tests
# =============================================================================
class TestPositionSnapshotSchema:
    """Tests for the PositionSnapshot schema."""

    def test_long_position(self):
        """Long position should have positive quantity."""
        position = PositionSnapshot(
            symbol="BBCA.JK",
            quantity=Decimal("1000"),
            average_entry_price=Decimal("9200.00"),
            current_price=Decimal("9350.00"),
            unrealized_pnl=Decimal("150000.00"),
            realized_pnl=Decimal("0.00"),
            market_value=Decimal("9350000.00"),
            strategy_id="momentum_v1",
            updated_at=datetime.now(UTC),
        )
        assert position.quantity > 0
        assert position.unrealized_pnl > 0

    def test_short_position(self):
        """Short position should have negative quantity."""
        position = PositionSnapshot(
            symbol="TLKM.JK",
            quantity=Decimal("-500"),
            average_entry_price=Decimal("3900.00"),
            current_price=Decimal("3850.00"),
            unrealized_pnl=Decimal("25000.00"),
            realized_pnl=Decimal("0.00"),
            market_value=Decimal("-1925000.00"),
            strategy_id="pairs_v1",
            updated_at=datetime.now(UTC),
        )
        assert position.quantity < 0

    def test_position_serialization(self):
        """Position snapshot should serialize to JSON correctly."""
        position = PositionSnapshot(
            symbol="BMRI.JK",
            quantity=Decimal("200"),
            average_entry_price=Decimal("6100.00"),
            current_price=Decimal("6200.00"),
            unrealized_pnl=Decimal("20000.00"),
            realized_pnl=Decimal("5000.00"),
            market_value=Decimal("1240000.00"),
            strategy_id="value_v1",
            updated_at=datetime.now(UTC),
        )
        data = position.model_dump(mode="json")
        assert "symbol" in data
        assert "unrealized_pnl" in data


# =============================================================================
# RiskLimits Schema Tests
# =============================================================================
class TestRiskLimitsSchema:
    """Tests for the RiskLimits schema."""

    def test_valid_risk_limits(self):
        """Valid risk limits should be created."""
        limits = RiskLimits(
            max_position_size=Decimal("10000000.00"),
            max_order_size=Decimal("1000000.00"),
            max_daily_loss=Decimal("500000.00"),
            max_drawdown_pct=Decimal("0.10"),
            max_var=Decimal("2000000.00"),
            max_concentration_pct=Decimal("0.25"),
            max_leverage=Decimal("2.0"),
        )
        assert limits.max_drawdown_pct == Decimal("0.10")
        assert limits.max_leverage == Decimal("2.0")

    @pytest.mark.parametrize(
        "field,value",
        [
            ("max_position_size", Decimal("-1")),
            ("max_daily_loss", Decimal("0")),
            ("max_drawdown_pct", Decimal("1.5")),
            ("max_concentration_pct", Decimal("-0.1")),
            ("max_leverage", Decimal("0")),
        ],
    )
    def test_invalid_risk_limits_rejected(self, field: str, value: Decimal):
        """Invalid risk limit values should raise ValidationError."""
        valid_data = {
            "max_position_size": Decimal("10000000"),
            "max_order_size": Decimal("1000000"),
            "max_daily_loss": Decimal("500000"),
            "max_drawdown_pct": Decimal("0.10"),
            "max_var": Decimal("2000000"),
            "max_concentration_pct": Decimal("0.25"),
            "max_leverage": Decimal("2.0"),
        }
        valid_data[field] = value
        with pytest.raises(ValidationError):
            RiskLimits(**valid_data)
