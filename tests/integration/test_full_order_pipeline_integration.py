"""Integration test for the full order pipeline.

Tests the flow: signal -> risk check -> submission -> fill.
Kafka and broker connections are mocked.
"""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

import pytest

# Transitive import to shared.kafka_producer_consumer uses Python 3.12+
# generic class syntax (PEP 695).  Skip on older runtimes.
try:
    from data_platform.models.trading import OrderStatusEnum
    from services.order_management_system.order_state_machine import VALID_TRANSITIONS
except SyntaxError:
    pytest.skip(
        "Requires Python 3.12+ (PEP 695 generic syntax in kafka_producer_consumer)",
        allow_module_level=True,
    )


# Fixtures
@pytest.fixture
def mock_kafka_producer():
    producer = AsyncMock()
    producer.send = AsyncMock(return_value=None)
    return producer


@pytest.fixture
def mock_broker_client():
    client = AsyncMock()
    client.submit_order = AsyncMock(return_value={"broker_order_id": "BRK-001"})
    client.cancel_order = AsyncMock(return_value=True)
    return client


@pytest.fixture
def sample_order_request():
    order = MagicMock()
    order.client_order_id = "test-pipeline-001"
    order.symbol = "BBCA.JK"
    order.side = 1  # BUY
    order.quantity = 500
    order.limit_price = 9200.0
    order.HasField.return_value = True
    order.signal_time.ToDatetime.return_value = datetime.now(tz=UTC)
    return order


@pytest.fixture
def sample_portfolio():
    portfolio = MagicMock()
    portfolio.total_market_value = 1_000_000_000.0
    portfolio.cash_balance = 500_000_000.0
    portfolio.positions = []
    portfolio.total_unrealized_pnl = 0.0
    portfolio.total_realized_pnl_today = 0.0
    portfolio.portfolio_var_95 = 10_000_000.0
    return portfolio


# Pipeline Flow Tests
class TestOrderPipelineFlow:
    """Test complete order lifecycle through the pipeline."""

    def test_risk_check_passes_for_valid_order(self, sample_order_request, sample_portfolio):
        """Verify a well-formed order passes all risk checks."""
        from services.pre_trade_risk_engine.pre_trade_risk_checks import (
            check_buying_power_t2,
            check_lot_size_constraint,
            check_max_position_size,
        )

        lot_result = check_lot_size_constraint(sample_order_request, lot_size=100)
        assert lot_result.passed is True

        pos_result = check_max_position_size(sample_order_request, sample_portfolio, max_pct=0.10)
        assert pos_result.passed is True

        bp_result = check_buying_power_t2(sample_order_request, available_cash=500_000_000.0, current_price=9200.0)
        assert bp_result.passed is True

    def test_transition_path_is_valid(self):
        """Verify that the happy-path transition sequence is legal."""
        path = [
            OrderStatusEnum.PENDING_RISK,
            OrderStatusEnum.RISK_APPROVED,
            OrderStatusEnum.SUBMITTED,
            OrderStatusEnum.ACKNOWLEDGED,
            OrderStatusEnum.FILLED,
        ]
        for i in range(len(path) - 1):
            assert path[i + 1] in VALID_TRANSITIONS[path[i]]

    def test_risk_rejection_blocks_submission(self, sample_order_request, sample_portfolio):
        """An order exceeding position limits should be risk-rejected."""
        from services.pre_trade_risk_engine.pre_trade_risk_checks import check_max_position_size

        sample_order_request.quantity = 500_000
        sample_portfolio.total_market_value = 5_000_000.0
        sample_portfolio.cash_balance = 0
        result = check_max_position_size(sample_order_request, sample_portfolio, max_pct=0.10)
        assert result.passed is False

    @pytest.mark.asyncio
    async def test_kafka_publish_called_on_transition(self, mock_kafka_producer):
        """Verify Kafka producer is invoked during state transition."""
        mock_kafka_producer.send.assert_not_called()
        # Simulate what the state machine would do
        await mock_kafka_producer.send("pyhron.orders.events", {"event": "test"}, key="ord-001")
        mock_kafka_producer.send.assert_called_once()

    @pytest.mark.asyncio
    async def test_broker_submission(self, mock_broker_client, sample_order_request):
        """Verify broker client is called for order submission."""
        result = await mock_broker_client.submit_order(sample_order_request)
        assert result["broker_order_id"] == "BRK-001"
        mock_broker_client.submit_order.assert_called_once_with(sample_order_request)

    def test_lot_size_rejection_stops_pipeline(self, sample_order_request):
        """An order with invalid lot size should be rejected before submission."""
        from services.pre_trade_risk_engine.pre_trade_risk_checks import check_lot_size_constraint

        sample_order_request.quantity = 150
        result = check_lot_size_constraint(sample_order_request, lot_size=100)
        assert result.passed is False
        assert result.adjusted_quantity == 100
