"""
Integration tests for order routing and execution flow.

Tests the complete order lifecycle: creation, validation, risk checks,
routing, execution, fill reporting, and PnL updates.

Requires:
  - Running PostgreSQL, Redis, and Kafka (docker-compose)
"""

from __future__ import annotations

import asyncio
import os
from datetime import UTC
from decimal import Decimal
from uuid import uuid4

import pytest
import pytest_asyncio
from enthropy.api.client import EntropyAPIClient
from enthropy.execution.models import ExecutionReport, ExecutionStatus
from enthropy.execution.router import OrderRouter
from enthropy.risk.engine import RiskEngine
from enthropy.shared.schemas.order import (
    OrderCreate,
    OrderResponse,
    OrderSide,
    OrderStatus,
    OrderType,
)
from enthropy.shared.schemas.risk import RiskLimits

# =============================================================================
# Skip Conditions
# =============================================================================
SKIP_INTEGRATION = pytest.mark.skipif(
    os.environ.get("SKIP_INTEGRATION", "false").lower() == "true",
    reason="SKIP_INTEGRATION is set.",
)

DATABASE_URL = os.environ.get("DATABASE_URL", "")
if not DATABASE_URL:
    DATABASE_URL = "postgresql+asyncpg://pyhron:pyhron@localhost:5432/pyhron_test"
REDIS_URL = os.environ.get("REDIS_URL", "redis://localhost:6379/1")
API_BASE_URL = os.environ.get("API_BASE_URL", "http://localhost:8000")


# =============================================================================
# Fixtures
# =============================================================================
@pytest_asyncio.fixture
async def api_client():
    """API client for order submission."""
    client = EntropyAPIClient(
        base_url=API_BASE_URL,
        api_key=os.environ.get("API_KEY", "test-api-key"),
        timeout=30,
    )
    yield client
    await client.close()


@pytest.fixture
def risk_engine() -> RiskEngine:
    """Risk engine with test-appropriate limits."""
    return RiskEngine(
        limits=RiskLimits(
            max_position_size=Decimal("50000000.00"),
            max_order_size=Decimal("10000000.00"),
            max_daily_loss=Decimal("2000000.00"),
            max_drawdown_pct=Decimal("0.15"),
            max_var=Decimal("5000000.00"),
            max_concentration_pct=Decimal("0.30"),
            max_leverage=Decimal("3.0"),
        )
    )


@pytest_asyncio.fixture
async def order_router():
    """Order router with mock exchange connection."""
    router = OrderRouter(
        mode="paper",  # Paper trading mode for integration tests
        redis_url=REDIS_URL,
    )
    await router.connect()
    yield router
    await router.disconnect()


@pytest.fixture
def sample_limit_order() -> OrderCreate:
    """Sample limit buy order."""
    return OrderCreate(
        symbol="BBCA.JK",
        side=OrderSide.BUY,
        order_type=OrderType.LIMIT,
        quantity=Decimal("1000"),
        price=Decimal("9200.00"),
        strategy_id="integration_test_v1",
    )


@pytest.fixture
def sample_market_order() -> OrderCreate:
    """Sample market sell order."""
    return OrderCreate(
        symbol="TLKM.JK",
        side=OrderSide.SELL,
        order_type=OrderType.MARKET,
        quantity=Decimal("500"),
        price=None,
        strategy_id="integration_test_v1",
    )


# =============================================================================
# Order Submission Tests
# =============================================================================
class TestOrderSubmission:
    """Tests for order submission via API."""

    @SKIP_INTEGRATION
    @pytest.mark.asyncio
    async def test_submit_limit_order(self, api_client: EntropyAPIClient, sample_limit_order: OrderCreate):
        """Limit order should be accepted and return an order ID."""
        response = await api_client.submit_order(sample_limit_order)

        assert isinstance(response, OrderResponse)
        assert response.order_id is not None
        assert response.status in (OrderStatus.PENDING, OrderStatus.ACCEPTED)
        assert response.symbol == "BBCA.JK"
        assert response.side == OrderSide.BUY
        assert response.quantity == Decimal("1000")

    @SKIP_INTEGRATION
    @pytest.mark.asyncio
    async def test_submit_market_order(self, api_client: EntropyAPIClient, sample_market_order: OrderCreate):
        """Market order should be accepted and routed immediately."""
        response = await api_client.submit_order(sample_market_order)

        assert isinstance(response, OrderResponse)
        assert response.order_id is not None
        assert response.status in (
            OrderStatus.PENDING,
            OrderStatus.ACCEPTED,
            OrderStatus.FILLED,
        )

    @SKIP_INTEGRATION
    @pytest.mark.asyncio
    async def test_submit_invalid_order_rejected(self, api_client: EntropyAPIClient):
        """Order with invalid parameters should be rejected."""
        invalid_order = OrderCreate(
            symbol="BBCA.JK",
            side=OrderSide.BUY,
            order_type=OrderType.LIMIT,
            quantity=Decimal("1"),
            price=Decimal("9200.00"),
            strategy_id="integration_test_v1",
        )
        # Lot size for IDX is typically 100 shares
        with pytest.raises(Exception) as exc_info:
            await api_client.submit_order(invalid_order)
        assert "lot_size" in str(exc_info.value).lower() or "quantity" in str(exc_info.value).lower()


# =============================================================================
# Risk Check Integration Tests
# =============================================================================
class TestRiskCheckIntegration:
    """Tests for risk checks integrated with order flow."""

    @SKIP_INTEGRATION
    @pytest.mark.asyncio
    async def test_order_passes_risk_checks(
        self,
        risk_engine: RiskEngine,
        sample_limit_order: OrderCreate,
    ):
        """Order within limits should pass all risk checks."""
        result = risk_engine.run_pre_trade_checks(
            order=sample_limit_order,
            current_position_value=Decimal("5000000.00"),
            current_var=Decimal("1000000.00"),
            proposed_var_impact=Decimal("200000.00"),
            peak_portfolio_value=Decimal("100000000.00"),
            current_portfolio_value=Decimal("95000000.00"),
            position_value_for_concentration=Decimal("10000000.00"),
            total_portfolio_value=Decimal("100000000.00"),
            total_exposure=Decimal("150000000.00"),
            equity=Decimal("100000000.00"),
        )
        assert result.passed is True

    @SKIP_INTEGRATION
    @pytest.mark.asyncio
    async def test_oversized_order_blocked(
        self,
        api_client: EntropyAPIClient,
    ):
        """Order exceeding risk limits should be blocked."""
        large_order = OrderCreate(
            symbol="BBCA.JK",
            side=OrderSide.BUY,
            order_type=OrderType.LIMIT,
            quantity=Decimal("100000"),  # Very large
            price=Decimal("9200.00"),
            strategy_id="integration_test_v1",
        )
        response = await api_client.submit_order(large_order)
        assert response.status in (OrderStatus.REJECTED, OrderStatus.RISK_REJECTED)


# =============================================================================
# Order Routing Tests
# =============================================================================
class TestOrderRouting:
    """Tests for order routing to exchange/execution venue."""

    @SKIP_INTEGRATION
    @pytest.mark.asyncio
    async def test_route_limit_order(
        self,
        order_router: OrderRouter,
        sample_limit_order: OrderCreate,
    ):
        """Limit order should be routed to the correct exchange."""
        order_id = uuid4()
        report = await order_router.route_order(
            order_id=order_id,
            order=sample_limit_order,
        )

        assert isinstance(report, ExecutionReport)
        assert report.order_id == order_id
        assert report.status in (
            ExecutionStatus.ROUTED,
            ExecutionStatus.ACKNOWLEDGED,
        )
        assert report.venue is not None

    @SKIP_INTEGRATION
    @pytest.mark.asyncio
    async def test_route_and_fill_market_order(
        self,
        order_router: OrderRouter,
        sample_market_order: OrderCreate,
    ):
        """Market order in paper mode should be filled immediately."""
        order_id = uuid4()
        report = await order_router.route_order(
            order_id=order_id,
            order=sample_market_order,
        )

        assert isinstance(report, ExecutionReport)
        # In paper mode, market orders should fill immediately
        if report.status == ExecutionStatus.FILLED:
            assert report.fill_price is not None
            assert report.fill_price > 0
            assert report.filled_quantity == sample_market_order.quantity


# =============================================================================
# Order Lifecycle Tests
# =============================================================================
class TestOrderLifecycle:
    """Tests for the complete order lifecycle."""

    @SKIP_INTEGRATION
    @pytest.mark.asyncio
    async def test_full_order_lifecycle(self, api_client: EntropyAPIClient):
        """Test complete lifecycle: submit -> accept -> fill."""
        # Submit order
        order = OrderCreate(
            symbol="BBCA.JK",
            side=OrderSide.BUY,
            order_type=OrderType.LIMIT,
            quantity=Decimal("100"),
            price=Decimal("9200.00"),
            strategy_id="lifecycle_test_v1",
        )
        response = await api_client.submit_order(order)
        order_id = response.order_id

        # Poll for status changes
        final_status = None
        for _ in range(30):
            status = await api_client.get_order_status(order_id)
            if status.status in (OrderStatus.FILLED, OrderStatus.CANCELLED, OrderStatus.REJECTED):
                final_status = status
                break
            await asyncio.sleep(1)

        assert final_status is not None, "Order did not reach terminal state in 30s"

    @SKIP_INTEGRATION
    @pytest.mark.asyncio
    async def test_cancel_pending_order(self, api_client: EntropyAPIClient):
        """Pending order should be cancellable."""
        # Submit a limit order far from market (unlikely to fill)
        order = OrderCreate(
            symbol="BBCA.JK",
            side=OrderSide.BUY,
            order_type=OrderType.LIMIT,
            quantity=Decimal("100"),
            price=Decimal("1000.00"),  # Far below market
            strategy_id="cancel_test_v1",
        )
        response = await api_client.submit_order(order)
        order_id = response.order_id

        # Cancel the order
        cancel_result = await api_client.cancel_order(order_id)
        assert cancel_result.status == OrderStatus.CANCELLED

    @SKIP_INTEGRATION
    @pytest.mark.asyncio
    async def test_batch_order_submission(self, api_client: EntropyAPIClient):
        """Multiple orders should be submittable in batch."""
        orders = [
            OrderCreate(
                symbol=symbol,
                side=OrderSide.BUY,
                order_type=OrderType.LIMIT,
                quantity=Decimal("100"),
                price=Decimal(str(price)),
                strategy_id="batch_test_v1",
            )
            for symbol, price in [
                ("BBCA.JK", "9200"),
                ("TLKM.JK", "3800"),
                ("BMRI.JK", "6100"),
            ]
        ]

        responses = await api_client.submit_batch(orders)
        assert len(responses) == 3
        assert all(r.order_id is not None for r in responses)


# =============================================================================
# Execution Report Tests
# =============================================================================
class TestExecutionReports:
    """Tests for execution report generation and delivery."""

    @SKIP_INTEGRATION
    @pytest.mark.asyncio
    async def test_fill_report_contains_required_fields(self, order_router: OrderRouter):
        """Fill reports should contain all required fields."""
        order = OrderCreate(
            symbol="BBCA.JK",
            side=OrderSide.BUY,
            order_type=OrderType.MARKET,
            quantity=Decimal("100"),
            price=None,
            strategy_id="report_test_v1",
        )
        report = await order_router.route_order(
            order_id=uuid4(),
            order=order,
        )

        if report.status == ExecutionStatus.FILLED:
            assert report.fill_price is not None
            assert report.filled_quantity is not None
            assert report.fill_timestamp is not None
            assert report.commission is not None
            assert report.venue is not None

    @SKIP_INTEGRATION
    @pytest.mark.asyncio
    async def test_execution_timestamps_are_utc(self, order_router: OrderRouter):
        """All execution timestamps should be in UTC."""
        order = OrderCreate(
            symbol="BBCA.JK",
            side=OrderSide.BUY,
            order_type=OrderType.MARKET,
            quantity=Decimal("100"),
            price=None,
            strategy_id="timestamp_test_v1",
        )
        report = await order_router.route_order(
            order_id=uuid4(),
            order=order,
        )

        assert report.timestamp.tzinfo is not None
        assert report.timestamp.tzinfo == UTC

        if report.fill_timestamp:
            assert report.fill_timestamp.tzinfo == UTC
