"""Alpaca paper account reconciliation.

Reconciles Pyhron OMS state against Alpaca paper account after each
fill event and on a polling interval during trading hours.
Alpaca is always the source of truth — Pyhron state is adjusted to match.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from datetime import UTC, datetime
from decimal import Decimal
from typing import TYPE_CHECKING, Any

from sqlalchemy import select, update

from data_platform.database_models.order_lifecycle_record import OrderLifecycleRecord, OrderStatusEnum
from data_platform.database_models.strategy_position_snapshot import StrategyPositionSnapshot
from shared.structured_json_logger import get_logger

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

    from data_platform.database_models.paper_trading_session import PaperTradingSession

logger = get_logger(__name__)


@dataclass
class ReconciliationDiscrepancy:
    """A single discrepancy between Pyhron and Alpaca state."""

    discrepancy_type: str  # POSITION_MISMATCH, ORDER_MISSING, FILL_MISSED, CASH_MISMATCH
    symbol: str | None
    order_id: str | None
    pyhron_value: str
    alpaca_value: str
    resolved: bool
    resolution: str | None


@dataclass
class ReconciliationReport:
    """Result of a reconciliation cycle."""

    session_id: str
    reconciled_at: datetime
    positions_checked: int
    orders_checked: int
    discrepancies: list[ReconciliationDiscrepancy] = field(default_factory=list)
    actions_taken: list[str] = field(default_factory=list)


class AlpacaPaperReconciliation:
    """Reconciles Pyhron OMS state against Alpaca paper account.

    Reconciliation runs:
    - After every fill event (event-driven)
    - Every 5 minutes during trading hours (polling fallback)
    - On session start (initial sync)

    Alpaca is always the source of truth. Pyhron state is adjusted
    to match Alpaca, never the reverse.
    """

    POSITION_SYNC_INTERVAL_SECONDS = 300
    ORDER_TIMEOUT_SECONDS = 60
    CASH_TOLERANCE_PCT = Decimal("0.01")

    def __init__(
        self,
        broker_adapter: Any = None,
        fill_processor: Any = None,
    ) -> None:
        self._broker = broker_adapter
        self._fill_processor = fill_processor

    async def run_reconciliation_loop(
        self,
        session: PaperTradingSession,
        db_session: AsyncSession,
    ) -> None:
        """Polling reconciliation loop, runs as background task."""
        while session.status == "RUNNING":
            try:
                await self.reconcile_positions(session, db_session)
                await self.reconcile_orders(session, db_session)
            except asyncio.CancelledError:
                break
            except Exception:
                logger.exception("reconciliation_loop_error", session_id=str(session.id))
            await asyncio.sleep(self.POSITION_SYNC_INTERVAL_SECONDS)

    async def reconcile_positions(
        self,
        session: PaperTradingSession,
        db_session: AsyncSession,
    ) -> ReconciliationReport:
        """Compare Pyhron positions against Alpaca positions."""
        now = datetime.now(UTC)
        report = ReconciliationReport(
            session_id=str(session.id),
            reconciled_at=now,
            positions_checked=0,
            orders_checked=0,
        )

        if self._broker is None:
            return report

        try:
            alpaca_positions = await self._broker.get_positions()
        except Exception:
            logger.exception("reconciliation_fetch_positions_failed")
            return report

        alpaca_by_symbol: dict[str, int] = {}
        for pos in alpaca_positions:
            symbol = pos.get("symbol", "")
            qty = int(pos.get("qty", 0))
            alpaca_by_symbol[symbol] = qty

        # Fetch Pyhron positions
        result = await db_session.execute(
            select(StrategyPositionSnapshot).where(
                StrategyPositionSnapshot.strategy_id == str(session.strategy_id),
            )
        )
        pyhron_positions = result.scalars().all()
        pyhron_by_symbol: dict[str, int] = {pos.symbol: pos.quantity for pos in pyhron_positions}

        all_symbols = set(alpaca_by_symbol.keys()) | set(pyhron_by_symbol.keys())
        report.positions_checked = len(all_symbols)

        for symbol in all_symbols:
            alpaca_qty = alpaca_by_symbol.get(symbol, 0)
            pyhron_qty = pyhron_by_symbol.get(symbol, 0)

            if alpaca_qty != pyhron_qty:
                discrepancy = ReconciliationDiscrepancy(
                    discrepancy_type="POSITION_MISMATCH",
                    symbol=symbol,
                    order_id=None,
                    pyhron_value=str(pyhron_qty),
                    alpaca_value=str(alpaca_qty),
                    resolved=True,
                    resolution=f"Updated Pyhron position from {pyhron_qty} to {alpaca_qty}",
                )
                report.discrepancies.append(discrepancy)
                report.actions_taken.append(f"Position {symbol}: {pyhron_qty} -> {alpaca_qty}")

                # Update Pyhron to match Alpaca
                await db_session.execute(
                    update(StrategyPositionSnapshot)
                    .where(
                        StrategyPositionSnapshot.strategy_id == str(session.strategy_id),
                        StrategyPositionSnapshot.symbol == symbol,
                    )
                    .values(quantity=alpaca_qty, last_updated=now)
                )

                logger.warning(
                    "position_mismatch_resolved",
                    symbol=symbol,
                    pyhron_qty=pyhron_qty,
                    alpaca_qty=alpaca_qty,
                )

        await db_session.flush()
        return report

    async def reconcile_orders(
        self,
        session: PaperTradingSession,
        db_session: AsyncSession,
    ) -> ReconciliationReport:
        """Compare recent orders against Alpaca order state."""
        now = datetime.now(UTC)
        report = ReconciliationReport(
            session_id=str(session.id),
            reconciled_at=now,
            positions_checked=0,
            orders_checked=0,
        )

        if self._broker is None:
            return report

        # Find orders in SUBMITTED state that might be stale
        result = await db_session.execute(
            select(OrderLifecycleRecord).where(
                OrderLifecycleRecord.strategy_id == str(session.strategy_id),
                OrderLifecycleRecord.status == OrderStatusEnum.SUBMITTED,
            )
        )
        submitted_orders = result.scalars().all()
        report.orders_checked = len(submitted_orders)

        for order in submitted_orders:
            if order.submitted_at is None:
                continue

            age = (now - order.submitted_at).total_seconds()
            if age < self.ORDER_TIMEOUT_SECONDS:
                continue

            # Check if order exists in Alpaca
            try:
                if order.broker_order_id:
                    alpaca_order = await self._broker.get_order_status(order.broker_order_id)
                    alpaca_status = alpaca_order.get("status", "")

                    if alpaca_status == "filled" and self._fill_processor:
                        # Missed fill — create synthetic
                        discrepancy = ReconciliationDiscrepancy(
                            discrepancy_type="FILL_MISSED",
                            symbol=order.symbol,
                            order_id=order.client_order_id,
                            pyhron_value="SUBMITTED",
                            alpaca_value="filled",
                            resolved=True,
                            resolution="Synthetic fill applied",
                        )
                        report.discrepancies.append(discrepancy)
                        await self.apply_synthetic_fill(alpaca_order, session, db_session)
                    elif alpaca_status in ("canceled", "expired"):
                        # Mark as cancelled
                        order.status = OrderStatusEnum.CANCELLED
                        order.updated_at = now
                        discrepancy = ReconciliationDiscrepancy(
                            discrepancy_type="ORDER_MISSING",
                            symbol=order.symbol,
                            order_id=order.client_order_id,
                            pyhron_value="SUBMITTED",
                            alpaca_value=alpaca_status,
                            resolved=True,
                            resolution=f"Marked as {alpaca_status}",
                        )
                        report.discrepancies.append(discrepancy)
            except Exception:
                logger.exception(
                    "reconciliation_order_check_failed",
                    order_id=order.client_order_id,
                )

        await db_session.flush()
        return report

    async def apply_synthetic_fill(
        self,
        alpaca_order: dict[str, Any],
        session: PaperTradingSession,
        db_session: AsyncSession,
    ) -> None:
        """Process a fill event from Alpaca data that was missed via Kafka."""
        if self._fill_processor is None:
            logger.warning("no_fill_processor_for_synthetic_fill")
            return

        fill_event = {
            "broker_order_id": alpaca_order.get("id", ""),
            "client_order_id": alpaca_order.get("client_order_id", ""),
            "filled_qty": alpaca_order.get("filled_qty", 0),
            "filled_avg_price": alpaca_order.get("filled_avg_price", "0"),
            "side": alpaca_order.get("side", ""),
            "symbol": alpaca_order.get("symbol", ""),
            "synthetic": True,
        }
        try:
            await self._fill_processor.process_fill(fill_event, db_session)
        except Exception:
            logger.exception("synthetic_fill_failed", order_id=alpaca_order.get("id"))
