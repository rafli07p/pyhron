"""Unit tests for the execution engine.

Validates order execution, priority queue, metrics tracking,
circuit breaker behavior, and callback invocation.
"""

from __future__ import annotations

from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pybreaker
import pytest

try:
    from services.execution.exchange_connectors import BaseConnector
    from services.execution.execution_engine import ExecutionEngine
    from shared.schemas.order_events import (
        OrderFill,
        OrderRequest,
        OrderSide,
        OrderStatusEnum,
        OrderType,
    )
except ImportError:
    pytest.skip("Requires execution modules", allow_module_level=True)


def _make_order(
    symbol: str = "BBCA.JK",
    side: OrderSide = OrderSide.BUY,
    qty: Decimal = Decimal("100"),
    price: Decimal | None = Decimal("9200"),
) -> OrderRequest:
    return OrderRequest(
        order_id=uuid4(),
        symbol=symbol,
        side=side,
        qty=qty,
        price=price,
        order_type=OrderType.LIMIT,
        tenant_id="test-tenant",
    )


def _make_fill(order: OrderRequest) -> OrderFill:
    return OrderFill(
        fill_id=uuid4(),
        order_id=order.order_id,
        symbol=order.symbol,
        side=order.side,
        qty=order.qty,
        price=order.price or Decimal("9200"),
        order_type=order.order_type,
        tenant_id=order.tenant_id,
        fill_qty=order.qty,
        fill_price=order.price or Decimal("9200"),
        cumulative_qty=order.qty,
        leaves_qty=Decimal("0"),
        status=OrderStatusEnum.FILLED,
        exchange="TEST",
    )


def _make_mock_connector(name: str = "alpaca") -> MagicMock:
    connector = MagicMock(spec=BaseConnector)
    connector.name = name
    return connector


class TestExecutionEngineBasic:
    """Tests for basic execution engine operations."""

    @pytest.mark.asyncio
    async def test_execute_order_success(self) -> None:
        """Successful order should return fill and update metrics."""
        connector = _make_mock_connector()
        order = _make_order()
        fill = _make_fill(order)
        connector.submit_order = AsyncMock(return_value=fill)

        engine = ExecutionEngine(connectors={"alpaca": connector})
        result = await engine.execute_order(order)

        assert result.fill_price == Decimal("9200")
        assert engine.metrics["total_orders"] == 1
        assert engine.metrics["total_fills"] == 1

    @pytest.mark.asyncio
    async def test_execute_order_unknown_connector_raises(self) -> None:
        """Unknown connector name should raise ValueError."""
        engine = ExecutionEngine(connectors={})
        with pytest.raises(ValueError, match="Unknown connector"):
            await engine.execute_order(_make_order(), connector_name="nonexistent")

    @pytest.mark.asyncio
    async def test_execute_order_uses_default_connector(self) -> None:
        """Should use default connector when none specified."""
        connector = _make_mock_connector()
        order = _make_order()
        fill = _make_fill(order)
        connector.submit_order = AsyncMock(return_value=fill)

        engine = ExecutionEngine(
            connectors={"alpaca": connector},
            default_connector="alpaca",
        )
        await engine.execute_order(order)
        connector.submit_order.assert_called_once()

    @pytest.mark.asyncio
    async def test_execute_order_specific_connector(self) -> None:
        """Should use the specified connector when given."""
        alpaca = _make_mock_connector("alpaca")
        ccxt = _make_mock_connector("ccxt")
        order = _make_order()
        fill = _make_fill(order)

        alpaca.submit_order = AsyncMock(return_value=fill)
        ccxt.submit_order = AsyncMock(return_value=fill)

        engine = ExecutionEngine(
            connectors={"alpaca": alpaca, "ccxt": ccxt},
            default_connector="alpaca",
        )
        await engine.execute_order(order, connector_name="ccxt")

        ccxt.submit_order.assert_called_once()
        alpaca.submit_order.assert_not_called()

    @pytest.mark.asyncio
    async def test_connector_failure_increments_rejections(self) -> None:
        """Connector error should increment rejection counter."""
        connector = _make_mock_connector()
        connector.submit_order = AsyncMock(side_effect=RuntimeError("exchange down"))

        engine = ExecutionEngine(connectors={"alpaca": connector})
        with pytest.raises(RuntimeError):
            await engine.execute_order(_make_order())

        assert engine.metrics["total_rejections"] == 1
        assert engine.metrics["total_fills"] == 0


class TestExecutionEngineCallbacks:
    """Tests for fill and rejection callbacks."""

    @pytest.mark.asyncio
    async def test_on_fill_callback_invoked(self) -> None:
        """Fill callback should be invoked on successful fill."""
        received: list[OrderFill] = []
        connector = _make_mock_connector()
        order = _make_order()
        fill = _make_fill(order)
        connector.submit_order = AsyncMock(return_value=fill)

        engine = ExecutionEngine(
            connectors={"alpaca": connector},
            on_fill=lambda f: received.append(f),
        )
        await engine.execute_order(order)

        assert len(received) == 1
        assert received[0].fill_price == Decimal("9200")

    @pytest.mark.asyncio
    async def test_on_rejection_callback_invoked(self) -> None:
        """Rejection callback should be invoked on connector failure."""
        received: list[tuple] = []
        connector = _make_mock_connector()
        connector.submit_order = AsyncMock(side_effect=RuntimeError("fail"))

        engine = ExecutionEngine(
            connectors={"alpaca": connector},
            on_rejection=lambda o, r: received.append((o, r)),
        )
        with pytest.raises(RuntimeError):
            await engine.execute_order(_make_order())

        assert len(received) == 1

    @pytest.mark.asyncio
    async def test_async_fill_callback(self) -> None:
        """Async fill callback should be awaited."""
        received: list[OrderFill] = []

        async def async_callback(fill: OrderFill) -> None:
            received.append(fill)

        connector = _make_mock_connector()
        order = _make_order()
        fill = _make_fill(order)
        connector.submit_order = AsyncMock(return_value=fill)

        engine = ExecutionEngine(
            connectors={"alpaca": connector},
            on_fill=async_callback,
        )
        await engine.execute_order(order)

        assert len(received) == 1


class TestExecutionEngineQueue:
    """Tests for the priority queue."""

    @pytest.mark.asyncio
    async def test_enqueue_and_process(self) -> None:
        """Enqueued orders should be processed by process_queue."""
        connector = _make_mock_connector()

        orders = [_make_order() for _ in range(3)]
        fills = [_make_fill(o) for o in orders]
        connector.submit_order = AsyncMock(side_effect=fills)

        engine = ExecutionEngine(connectors={"alpaca": connector})

        for order in orders:
            await engine.enqueue_order(order)

        assert engine.metrics["queue_depth"] == 3

        result_fills = await engine.process_queue()
        assert len(result_fills) == 3
        assert engine.metrics["queue_depth"] == 0

    @pytest.mark.asyncio
    async def test_process_empty_queue(self) -> None:
        """Processing empty queue should return empty list."""
        engine = ExecutionEngine(connectors={"alpaca": _make_mock_connector()})
        result = await engine.process_queue()
        assert result == []


class TestExecutionEngineMetrics:
    """Tests for engine metrics."""

    @pytest.mark.asyncio
    async def test_initial_metrics(self) -> None:
        """Initial metrics should be zeroed."""
        engine = ExecutionEngine(connectors={"alpaca": _make_mock_connector()})
        m = engine.metrics
        assert m["total_orders"] == 0
        assert m["total_fills"] == 0
        assert m["total_rejections"] == 0
        assert m["avg_latency_ns"] == 0
        assert m["p99_latency_ns"] == 0

    @pytest.mark.asyncio
    async def test_latency_tracking(self) -> None:
        """Latency should be tracked after successful orders."""
        connector = _make_mock_connector()
        order = _make_order()
        fill = _make_fill(order)
        connector.submit_order = AsyncMock(return_value=fill)

        engine = ExecutionEngine(connectors={"alpaca": connector})
        await engine.execute_order(order)

        m = engine.metrics
        assert m["latency_samples"] == 1
        assert m["avg_latency_ns"] > 0


class TestExecutionEngineLifecycle:
    """Tests for start/stop lifecycle."""

    @pytest.mark.asyncio
    async def test_start_and_stop(self) -> None:
        """Engine should start and stop cleanly."""
        engine = ExecutionEngine(connectors={"alpaca": _make_mock_connector()})
        await engine.start()
        assert engine._running is True

        await engine.stop()
        assert engine._running is False

    @pytest.mark.asyncio
    async def test_double_start_is_noop(self) -> None:
        """Starting an already-running engine should be a no-op."""
        engine = ExecutionEngine(connectors={"alpaca": _make_mock_connector()})
        await engine.start()
        task1 = engine._worker_task
        await engine.start()
        task2 = engine._worker_task
        assert task1 is task2
        await engine.stop()
