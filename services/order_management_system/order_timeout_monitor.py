"""Order timeout monitor for the Pyhron OMS.

Periodically scans for unfilled orders that have exceeded their time-to-live
and transitions them to EXPIRED status. Prevents stale orders from remaining
open indefinitely.
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timedelta, timezone

from sqlalchemy import select

from data_platform.models.trading import Order, OrderStatusEnum
from services.order_management_system.order_state_machine import OrderStateMachine
from shared.configuration_settings import get_config
from shared.structured_json_logger import get_logger
from shared.kafka_producer_consumer import PyhronProducer

logger = get_logger(__name__)

# Default timeout configurations
DEFAULT_SCAN_INTERVAL_SECONDS: int = 60  # How often to scan for expired orders
DEFAULT_ORDER_TTL_SECONDS: int = 300  # 5 minutes for market orders
DEFAULT_LIMIT_ORDER_TTL_SECONDS: int = 28800  # 8 hours for limit orders (full trading session)

# Statuses that can be expired
EXPIRABLE_STATUSES: set[OrderStatusEnum] = {
    OrderStatusEnum.SUBMITTED,
    OrderStatusEnum.ACKNOWLEDGED,
}


class OrderTimeoutMonitor:
    """Monitors and expires unfilled orders that exceed their time-to-live.

    Runs a periodic scan loop that:
      1. Queries for orders in SUBMITTED or ACKNOWLEDGED status.
      2. Checks if each order has exceeded its TTL based on order type.
      3. Transitions expired orders to EXPIRED status via the state machine.

    Market orders have a shorter TTL (default 5 minutes) while limit orders
    have a longer TTL (default 8 hours / full trading session).

    Usage::

        monitor = OrderTimeoutMonitor(producer)
        await monitor.start()
        await monitor.run()
    """

    def __init__(
        self,
        producer: PyhronProducer,
        scan_interval_seconds: int = DEFAULT_SCAN_INTERVAL_SECONDS,
        market_order_ttl_seconds: int = DEFAULT_ORDER_TTL_SECONDS,
        limit_order_ttl_seconds: int = DEFAULT_LIMIT_ORDER_TTL_SECONDS,
    ) -> None:
        """Initialize the timeout monitor.

        Args:
            producer: Kafka producer for the state machine.
            scan_interval_seconds: How often to scan for expired orders.
            market_order_ttl_seconds: TTL for market orders.
            limit_order_ttl_seconds: TTL for limit orders.
        """
        self._state_machine = OrderStateMachine(producer)
        self._scan_interval: int = scan_interval_seconds
        self._market_order_ttl: int = market_order_ttl_seconds
        self._limit_order_ttl: int = limit_order_ttl_seconds
        self._running: bool = False

    async def start(self) -> None:
        """Start the timeout monitor."""
        self._running = True
        logger.info(
            "order_timeout_monitor_started",
            scan_interval_seconds=self._scan_interval,
            market_order_ttl_seconds=self._market_order_ttl,
            limit_order_ttl_seconds=self._limit_order_ttl,
        )

    async def stop(self) -> None:
        """Stop the timeout monitor."""
        self._running = False
        logger.info("order_timeout_monitor_stopped")

    async def run(self) -> None:
        """Main loop: periodically scan for and expire timed-out orders."""
        while self._running:
            try:
                expired_count = await self.scan_and_expire()
                if expired_count > 0:
                    logger.info(
                        "timeout_scan_complete",
                        expired_count=expired_count,
                    )
            except Exception:
                logger.exception("timeout_scan_failed")

            await asyncio.sleep(self._scan_interval)

    async def scan_and_expire(self) -> int:
        """Execute a single scan for expired orders.

        Queries the database for orders in expirable statuses, checks
        each against its TTL, and transitions expired ones.

        Returns:
            Number of orders expired in this scan.
        """
        from shared.async_database_session import get_session

        now = datetime.now(tz=timezone.utc)
        expired_count = 0

        async with get_session() as session:
            result = await session.execute(
                select(Order).where(
                    Order.status.in_(list(EXPIRABLE_STATUSES)),
                )
            )
            orders = result.scalars().all()

        for order in orders:
            if self._is_expired(order, now):
                try:
                    await self._expire_order(order)
                    expired_count += 1
                except Exception:
                    logger.exception(
                        "order_expiry_failed",
                        client_order_id=order.client_order_id,
                    )

        return expired_count

    def _is_expired(self, order: Order, now: datetime) -> bool:
        """Check whether an order has exceeded its TTL.

        Uses the order's ``submitted_at`` or ``created_at`` timestamp
        and compares against the appropriate TTL based on order type.

        Args:
            order: The order to check.
            now: Current UTC timestamp.

        Returns:
            True if the order has exceeded its TTL.
        """
        reference_time = order.submitted_at or order.created_at
        if reference_time is None:
            return False

        # Ensure timezone awareness
        if reference_time.tzinfo is None:
            reference_time = reference_time.replace(tzinfo=timezone.utc)

        # Determine TTL based on order type
        if order.order_type in ("LIMIT", "STOP_LIMIT"):
            ttl = self._limit_order_ttl
        else:
            ttl = self._market_order_ttl

        expiry_time = reference_time + timedelta(seconds=ttl)
        return now >= expiry_time

    async def _expire_order(self, order: Order) -> None:
        """Transition an order to EXPIRED status.

        Args:
            order: The order to expire.
        """
        await self._state_machine.transition(
            order=order,
            to_status=OrderStatusEnum.EXPIRED,
            event_data={
                "rejection_reason": (
                    f"Order timed out after exceeding TTL. "
                    f"Order type: {order.order_type}, "
                    f"Status: {order.status.value}"
                ),
            },
            source="timeout_monitor",
        )

        logger.info(
            "order_expired_by_timeout",
            client_order_id=order.client_order_id,
            order_type=order.order_type,
            previous_status=order.status.value,
        )
