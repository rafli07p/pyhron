"""Unit tests for BrokerOrderMapper.

Tests Alpaca and IDX FIX format conversion, round-trip integrity,
and unsupported broker error handling.
"""

from __future__ import annotations

import pytest

try:
    from services.broker_connectivity.broker_order_mapper import (
        ALPACA_ORDER_TYPE_MAP,
        ALPACA_SIDE_MAP,
        ALPACA_TIF_MAP,
        BrokerOrderMapper,
    )
    from shared.proto_generated.equity_orders_pb2 import (
        OrderRequest,
        OrderSide,
        OrderType,
        TimeInForce,
    )
except (ImportError, SyntaxError):
    pytest.skip(
        "Requires protobuf generated code or Python 3.12+",
        allow_module_level=True,
    )


@pytest.fixture()
def mapper() -> BrokerOrderMapper:
    return BrokerOrderMapper()


@pytest.fixture()
def sample_limit_order() -> OrderRequest:
    order = OrderRequest()
    order.client_order_id = "test-order-001"
    order.symbol = "BBCA"
    order.side = OrderSide.ORDER_SIDE_BUY
    order.order_type = OrderType.ORDER_TYPE_LIMIT
    order.quantity = 500
    order.limit_price = 9250.0
    order.time_in_force = TimeInForce.TIME_IN_FORCE_DAY
    return order


@pytest.fixture()
def sample_market_order() -> OrderRequest:
    order = OrderRequest()
    order.client_order_id = "test-order-002"
    order.symbol = "BBRI"
    order.side = OrderSide.ORDER_SIDE_SELL
    order.order_type = OrderType.ORDER_TYPE_MARKET
    order.quantity = 1000
    order.time_in_force = TimeInForce.TIME_IN_FORCE_DAY
    return order


# Alpaca Mapping Tests
class TestAlpacaMapping:
    def test_limit_buy_to_alpaca(self, mapper: BrokerOrderMapper, sample_limit_order: OrderRequest) -> None:
        payload = mapper.to_alpaca_order(sample_limit_order)
        assert payload["symbol"] == "BBCA"
        assert payload["side"] == "buy"
        assert payload["type"] == "limit"
        assert payload["qty"] == "500"
        assert payload["limit_price"] == "9250.0"
        assert payload["client_order_id"] == "test-order-001"
        assert payload["time_in_force"] == "day"

    def test_market_sell_to_alpaca(self, mapper: BrokerOrderMapper, sample_market_order: OrderRequest) -> None:
        payload = mapper.to_alpaca_order(sample_market_order)
        assert payload["symbol"] == "BBRI"
        assert payload["side"] == "sell"
        assert payload["type"] == "market"
        assert payload["qty"] == "1000"
        assert "limit_price" not in payload

    def test_alpaca_roundtrip(self, mapper: BrokerOrderMapper, sample_limit_order: OrderRequest) -> None:
        alpaca_payload = mapper.to_alpaca_order(sample_limit_order)
        restored = mapper.from_alpaca_order(alpaca_payload)
        assert restored.symbol == sample_limit_order.symbol
        assert restored.side == sample_limit_order.side
        assert restored.order_type == sample_limit_order.order_type
        assert restored.quantity == sample_limit_order.quantity

    def test_from_alpaca_position(self, mapper: BrokerOrderMapper) -> None:
        data = {
            "symbol": "AAPL",
            "qty": "100",
            "avg_entry_price": "150.50",
            "market_value": "15200.00",
            "unrealized_pl": "150.00",
            "current_price": "152.00",
        }
        pos = mapper.from_alpaca_position(data)
        assert pos.symbol == "AAPL"
        assert pos.quantity == 100
        assert pos.avg_entry_price == pytest.approx(150.50)
        assert pos.current_price == pytest.approx(152.00)


# IDX FIX Mapping Tests
class TestIDXFIXMapping:
    def test_limit_buy_to_fix(self, mapper: BrokerOrderMapper, sample_limit_order: OrderRequest) -> None:
        tags = mapper.to_fix_new_order(sample_limit_order)
        assert tags["35"] == "D"  # NewSingleOrder
        assert tags["55"] == "BBCA"  # Symbol
        assert tags["54"] == "1"  # Side: Buy
        assert tags["40"] == "2"  # OrdType: Limit
        assert tags["38"] == "500"  # OrderQty
        assert tags["44"] == "9250.00"  # Price
        assert tags["207"] == "XIDX"  # SecurityExchange

    def test_market_sell_to_fix(self, mapper: BrokerOrderMapper, sample_market_order: OrderRequest) -> None:
        tags = mapper.to_fix_new_order(sample_market_order)
        assert tags["54"] == "2"  # Side: Sell
        assert tags["40"] == "1"  # OrdType: Market
        assert "44" not in tags  # No price for market orders

    def test_fix_execution_report_parsing(self, mapper: BrokerOrderMapper) -> None:
        tags = {
            "37": "BROKER-123",
            "11": "test-order-001",
            "150": "F",  # ExecType: Fill
            "55": "BBCA",
            "32": "500",  # LastQty
            "31": "9250",  # LastPx
            "14": "500",  # CumQty
            "6": "9250",  # AvgPx
            "39": "2",  # OrdStatus: Filled
            "58": "Order filled",
        }
        result = mapper.from_fix_execution_report(tags)
        assert result["broker_order_id"] == "BROKER-123"
        assert result["client_order_id"] == "test-order-001"
        assert result["filled_quantity"] == 500
        assert result["filled_price"] == 9250.0
        assert result["broker_name"] == "IDX"


# Unified Broker Interface Tests
class TestUnifiedBrokerInterface:
    def test_to_broker_alpaca(self, mapper: BrokerOrderMapper, sample_limit_order: OrderRequest) -> None:
        payload = mapper.to_broker(sample_limit_order, "ALPACA")
        assert payload.broker_name == "ALPACA"
        assert payload.payload["symbol"] == "BBCA"

    def test_to_broker_idx(self, mapper: BrokerOrderMapper, sample_limit_order: OrderRequest) -> None:
        payload = mapper.to_broker(sample_limit_order, "IDX")
        assert payload.broker_name == "IDX"
        assert payload.payload["55"] == "BBCA"

    def test_to_broker_case_insensitive(self, mapper: BrokerOrderMapper, sample_limit_order: OrderRequest) -> None:
        payload = mapper.to_broker(sample_limit_order, "alpaca")
        assert payload.broker_name == "ALPACA"

    def test_to_broker_unsupported_raises(self, mapper: BrokerOrderMapper, sample_limit_order: OrderRequest) -> None:
        with pytest.raises(ValueError, match="Unsupported broker"):
            mapper.to_broker(sample_limit_order, "BINANCE")

    def test_from_broker_alpaca(self, mapper: BrokerOrderMapper) -> None:
        data = {
            "id": "alpaca-123",
            "client_order_id": "test-001",
            "symbol": "AAPL",
            "side": "buy",
            "type": "limit",
            "qty": "100",
            "limit_price": "150.00",
            "filled_qty": "50",
            "filled_avg_price": "149.50",
            "status": "partially_filled",
        }
        result = mapper.from_broker(data, "ALPACA")
        assert result["broker_order_id"] == "alpaca-123"
        assert result["symbol"] == "AAPL"
        assert result["filled_qty"] == 50
        assert result["broker_name"] == "ALPACA"

    def test_from_broker_idx(self, mapper: BrokerOrderMapper) -> None:
        tags = {
            "37": "IDX-456",
            "11": "test-002",
            "55": "BBCA",
            "150": "F",
            "32": "100",
            "31": "9250",
            "14": "100",
            "6": "9250",
            "39": "2",
        }
        result = mapper.from_broker(tags, "IDX")
        assert result["broker_order_id"] == "IDX-456"
        assert result["broker_name"] == "IDX"

    def test_from_broker_unsupported_raises(self, mapper: BrokerOrderMapper) -> None:
        with pytest.raises(ValueError, match="Unsupported broker"):
            mapper.from_broker({}, "BINANCE")


# Side/Type Map Coverage
class TestMappingCoverage:
    def test_all_sides_mapped_for_alpaca(self) -> None:
        assert OrderSide.ORDER_SIDE_BUY in ALPACA_SIDE_MAP
        assert OrderSide.ORDER_SIDE_SELL in ALPACA_SIDE_MAP

    def test_all_order_types_mapped_for_alpaca(self) -> None:
        for ot in [
            OrderType.ORDER_TYPE_MARKET,
            OrderType.ORDER_TYPE_LIMIT,
            OrderType.ORDER_TYPE_STOP,
            OrderType.ORDER_TYPE_STOP_LIMIT,
        ]:
            assert ot in ALPACA_ORDER_TYPE_MAP

    def test_all_tif_mapped_for_alpaca(self) -> None:
        for tif in [
            TimeInForce.TIME_IN_FORCE_DAY,
            TimeInForce.TIME_IN_FORCE_GTC,
            TimeInForce.TIME_IN_FORCE_IOC,
            TimeInForce.TIME_IN_FORCE_FOK,
        ]:
            assert tif in ALPACA_TIF_MAP

    def test_idx_lot_size_metadata(self, mapper: BrokerOrderMapper, sample_limit_order: OrderRequest) -> None:
        payload = mapper.to_broker(sample_limit_order, "IDX")
        assert payload.metadata["lot_size_valid"] == (sample_limit_order.quantity % 100 == 0)
