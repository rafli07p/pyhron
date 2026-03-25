"""Low-latency execution engine for the Pyhron trading platform.

Provides an async priority queue, concurrent order dispatch via
:func:`asyncio.gather`, circuit-breaker protection (``pybreaker``), and
nanosecond-resolution latency tracking.

.. note::

   # FFI Extension Point
   # -------------------
   # For ultra-low-latency hot paths (< 100us), this module is designed
   # to be extended with a Rust or Go shared library via ctypes / cffi.
   # The ``_submit_order_native()`` placeholder below marks the
   # integration point.  A compiled ``libexec_engine.so`` exposing a
   # C-compatible ``submit_order(const char* json) -> const char*``
   # function can be loaded at startup and called from
   # ``_try_native_submit()``.
"""

from __future__ import annotations

import asyncio
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, Optional, cast
from uuid import UUID

import pybreaker
import structlog

from services.execution.exchange_connectors import BaseConnector
from shared.schemas.order_events import (
    OrderFill,
    OrderRequest,
    OrderStatusEnum,
)

logger = structlog.get_logger(__name__)


# ---------------------------------------------------------------------------
# Circuit breaker for exchange failures
# ---------------------------------------------------------------------------

exchange_breaker = pybreaker.CircuitBreaker(
    fail_max=5,
    reset_timeout=30,
    name="exchange_circuit_breaker",
)


# ---------------------------------------------------------------------------
# Priority wrapper for the queue
# ---------------------------------------------------------------------------


@dataclass(order=True)
class _PrioritisedOrder:
    """Wrapper that makes :class:`OrderRequest` sortable by priority.

    Lower ``priority`` values execute first (0 = highest priority).
    ``sequence`` is a tie-breaker ensuring FIFO within the same level.
    """

    priority: int
    sequence: int
    order: OrderRequest = field(compare=False)


# ---------------------------------------------------------------------------
# ExecutionEngine
# ---------------------------------------------------------------------------


class ExecutionEngine:
    """Async low-latency execution engine.

    Parameters
    ----------
    connectors:
        Mapping of connector name -> :class:`BaseConnector` instance.
    default_connector:
        Name of the connector to use when the order does not specify one.
    max_concurrent:
        Maximum number of orders dispatched concurrently via
        :func:`asyncio.gather`.
    on_fill:
        Optional callback invoked on every successful fill.
    on_rejection:
        Optional callback invoked on every rejection.
    """

    def __init__(
        self,
        connectors: dict[str, BaseConnector],
        default_connector: str = "alpaca",
        max_concurrent: int = 10,
        on_fill: Callable[[OrderFill], Any] | None = None,
        on_rejection: Callable[[OrderRequest, str], Any] | None = None,
    ) -> None:
        self._connectors = connectors
        self._default_connector = default_connector
        self._max_concurrent = max_concurrent
        self._on_fill = on_fill
        self._on_rejection = on_rejection

        self._queue: asyncio.PriorityQueue[_PrioritisedOrder] = asyncio.PriorityQueue()
        self._sequence = 0
        self._running = False
        self._worker_task: asyncio.Task[None] | None = None

        # Metrics
        self._total_orders = 0
        self._total_fills = 0
        self._total_rejections = 0
        self._latency_samples: list[int] = []  # nanoseconds

    # -- public API ----------------------------------------------------------

    async def start(self) -> None:
        """Start the background queue processor."""
        if self._running:
            return
        self._running = True
        self._worker_task = asyncio.create_task(self._process_queue_loop())
        logger.info("engine.started", max_concurrent=self._max_concurrent)

    async def stop(self) -> None:
        """Drain the queue and stop processing."""
        self._running = False
        if self._worker_task is not None:
            self._worker_task.cancel()
            try:
                await self._worker_task
            except asyncio.CancelledError:
                pass
            self._worker_task = None
        logger.info(
            "engine.stopped",
            total_orders=self._total_orders,
            total_fills=self._total_fills,
            total_rejections=self._total_rejections,
        )

    async def execute_order(self, order: OrderRequest, *, connector_name: str | None = None) -> OrderFill:
        """Submit a single order immediately (bypass queue).

        This is the fast path -- the order is sent directly to the
        connector with nanosecond latency measurement.
        """
        name = connector_name or self._default_connector
        connector = self._connectors.get(name)
        if connector is None:
            raise ValueError(f"Unknown connector: {name}")

        self._total_orders += 1
        t0 = time.perf_counter_ns()

        try:
            # --- Rust/Go FFI extension point ---
            # native_result = self._try_native_submit(order)
            # if native_result is not None:
            #     return native_result

            fill = cast(OrderFill, await self._submit_with_breaker(connector, order))
            latency_ns = time.perf_counter_ns() - t0
            self._latency_samples.append(latency_ns)
            self._total_fills += 1

            logger.info(
                "engine.order_executed",
                order_id=str(order.order_id),
                connector=name,
                latency_ns=latency_ns,
                latency_us=latency_ns / 1_000,
                fill_price=str(fill.fill_price),
            )

            await self._handle_fill(fill)
            return fill

        except pybreaker.CircuitBreakerError:
            latency_ns = time.perf_counter_ns() - t0
            self._total_rejections += 1
            reason = f"Circuit breaker open for connector '{name}'"
            logger.error("engine.circuit_breaker_open", connector=name, latency_ns=latency_ns)
            await self._handle_rejection(order, reason)
            raise

        except Exception as exc:
            latency_ns = time.perf_counter_ns() - t0
            self._total_rejections += 1
            reason = f"{type(exc).__name__}: {exc}"
            logger.error(
                "engine.order_failed",
                order_id=str(order.order_id),
                connector=name,
                latency_ns=latency_ns,
                error=reason,
            )
            await self._handle_rejection(order, reason)
            raise

    async def enqueue_order(self, order: OrderRequest, *, connector_name: str | None = None) -> None:
        """Add an order to the priority queue for deferred execution."""
        self._sequence += 1
        item = _PrioritisedOrder(
            priority=getattr(order, "priority", 5) if hasattr(order, "priority") else 5,
            sequence=self._sequence,
            order=order,
        )
        await self._queue.put(item)
        logger.info(
            "engine.order_enqueued",
            order_id=str(order.order_id),
            priority=item.priority,
            queue_size=self._queue.qsize(),
        )

    # -- queue processing ----------------------------------------------------

    async def _process_queue_loop(self) -> None:
        """Continuously drain the priority queue in batches."""
        while self._running:
            batch: list[_PrioritisedOrder] = []
            try:
                # Block until at least one order arrives
                first = await asyncio.wait_for(self._queue.get(), timeout=1.0)
                batch.append(first)
            except TimeoutError:
                continue

            # Grab up to max_concurrent - 1 additional items without blocking
            while len(batch) < self._max_concurrent and not self._queue.empty():
                try:
                    batch.append(self._queue.get_nowait())
                except asyncio.QueueEmpty:
                    break

            # Dispatch batch concurrently
            tasks = [self.execute_order(item.order) for item in batch]
            results = await asyncio.gather(*tasks, return_exceptions=True)

            for item, result in zip(batch, results):
                if isinstance(result, Exception):
                    logger.error(
                        "engine.batch_order_failed",
                        order_id=str(item.order.order_id),
                        error=str(result),
                    )

    async def process_queue(self) -> list[OrderFill]:
        """Process all currently queued orders and return fills.

        Unlike :meth:`_process_queue_loop`, this runs once and returns.
        Useful for testing and manual flush.
        """
        fills: list[OrderFill] = []
        batch: list[_PrioritisedOrder] = []
        while not self._queue.empty():
            try:
                batch.append(self._queue.get_nowait())
            except asyncio.QueueEmpty:
                break

        if not batch:
            return fills

        tasks = [self.execute_order(item.order) for item in batch]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        for item, result in zip(batch, results):
            if isinstance(result, OrderFill):
                fills.append(result)
            elif isinstance(result, Exception):
                logger.error(
                    "engine.flush_order_failed",
                    order_id=str(item.order.order_id),
                    error=str(result),
                )
        return fills

    # -- circuit-breaker wrapper ---------------------------------------------

    @exchange_breaker
    async def _submit_with_breaker(self, connector: BaseConnector, order: OrderRequest) -> OrderFill:
        """Submit through the circuit breaker."""
        return await connector.submit_order(order)

    # -- callbacks -----------------------------------------------------------

    async def _handle_fill(self, fill: OrderFill) -> None:
        """Post-fill processing: invoke callback, emit metrics."""
        if self._on_fill is not None:
            try:
                result = self._on_fill(fill)
                if asyncio.iscoroutine(result):
                    await result
            except Exception:
                logger.exception("engine.on_fill_callback_error", fill_id=str(fill.fill_id))

    async def _handle_rejection(self, order: OrderRequest, reason: str) -> None:
        """Post-rejection processing: invoke callback, emit metrics."""
        if self._on_rejection is not None:
            try:
                result = self._on_rejection(order, reason)
                if asyncio.iscoroutine(result):
                    await result
            except Exception:
                logger.exception("engine.on_rejection_callback_error", order_id=str(order.order_id))

    # -- Rust / Go FFI placeholder -------------------------------------------

    # def _try_native_submit(self, order: OrderRequest) -> Optional[OrderFill]:
    #     """Attempt to submit via a compiled native library for sub-microsecond
    #     execution.
    #
    #     Load ``libexec_engine.so`` (Rust) or ``libexec_engine.so`` (Go cgo)
    #     via ctypes:
    #
    #         import ctypes
    #         _lib = ctypes.CDLL("./libexec_engine.so")
    #         _lib.submit_order.argtypes = [ctypes.c_char_p]
    #         _lib.submit_order.restype = ctypes.c_char_p
    #
    #     Returns None if the native library is not available, causing the
    #     engine to fall back to the pure-Python async path.
    #     """
    #     return None

    # -- metrics -------------------------------------------------------------

    @property
    def metrics(self) -> dict[str, Any]:
        """Return a snapshot of engine performance metrics."""
        avg_latency = (
            sum(self._latency_samples) / len(self._latency_samples)
            if self._latency_samples
            else 0
        )
        p99_latency = (
            sorted(self._latency_samples)[int(len(self._latency_samples) * 0.99)]
            if self._latency_samples
            else 0
        )
        return {
            "total_orders": self._total_orders,
            "total_fills": self._total_fills,
            "total_rejections": self._total_rejections,
            "queue_depth": self._queue.qsize(),
            "avg_latency_ns": int(avg_latency),
            "avg_latency_us": avg_latency / 1_000,
            "p99_latency_ns": p99_latency,
            "latency_samples": len(self._latency_samples),
        }


__all__ = [
    "ExecutionEngine",
]
