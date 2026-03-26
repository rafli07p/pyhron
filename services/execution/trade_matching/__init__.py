"""Internal trade-matching engine for the Pyhron trading platform.

Implements a price-time priority order book for paper trading and
dark-pool simulation.  Uses :mod:`heapq` for efficient bid/ask heaps
and :class:`threading.Lock` for thread safety.  Emits
:class:`~shared.schemas.order_events.OrderFill` events on every match.
"""

from __future__ import annotations

import heapq
import threading
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime, timezone
from decimal import Decimal
from typing import Any, Optional
from uuid import UUID, uuid4

import structlog

from shared.schemas.order_events import (
    OrderFill,
    OrderRequest,
    OrderSide,
    OrderStatusEnum,
    OrderType,
)

logger = structlog.get_logger(__name__)


# Internal order representation


@dataclass
class BookOrder:
    """An order resting on the internal order book."""

    order_id: UUID
    symbol: str
    side: OrderSide
    price: Decimal          # limit price (Decimal("0") for market)
    quantity: Decimal        # original quantity
    remaining: Decimal       # unfilled quantity
    timestamp: datetime
    tenant_id: str
    sequence: int            # monotonic counter for time priority
    cancelled: bool = False

    # heap comparison helpers ------------------------------------------------
    # Bids: highest price first  -> negate price for min-heap
    # Asks: lowest price first   -> use price directly

    def bid_key(self) -> tuple[Decimal, int]:
        return (-self.price, self.sequence)

    def ask_key(self) -> tuple[Decimal, int]:
        return (self.price, self.sequence)


@dataclass(order=True)
class _HeapEntry:
    """Wrapper to store :class:`BookOrder` in a :mod:`heapq` min-heap."""

    key: tuple[Decimal, int]
    order: BookOrder = field(compare=False)


# TradeMatchingEngine


class TradeMatchingEngine:
    """Price-time priority matching engine for paper trading.

    Maintains per-symbol order books with bid and ask heaps.  When a new
    order is added, the engine immediately attempts to match it against
    the opposite side of the book.  Any resulting fills are emitted via
    the optional ``on_fill`` callback.

    Thread safety is guaranteed by a :class:`threading.Lock` around all
    mutations.

    Parameters
    ----------
    on_fill:
        Optional callback ``(OrderFill) -> None`` invoked on every match.
    """

    def __init__(self, on_fill: Callable[[OrderFill], Any] | None = None) -> None:
        self._lock = threading.Lock()
        self._on_fill = on_fill
        self._sequence = 0

        # Per-symbol order books: symbol -> {"bids": [...], "asks": [...]}
        self._books: dict[str, dict[str, list[_HeapEntry]]] = {}

        # Quick lookup by order_id
        self._orders: dict[UUID, BookOrder] = {}

    # -- public API ----------------------------------------------------------

    def add_order(self, order: OrderRequest) -> list[OrderFill]:
        """Add an order and attempt to match it immediately.

        Returns a list of :class:`OrderFill` events generated during
        matching.  The list is empty if the order rests on the book
        without being (partially) filled.
        """
        with self._lock:
            self._sequence += 1

            price = order.price if order.price is not None else Decimal("0")
            book_order = BookOrder(
                order_id=order.order_id,
                symbol=order.symbol,
                side=order.side,
                price=price,
                quantity=order.qty,
                remaining=order.qty,
                timestamp=datetime.now(UTC),
                tenant_id=order.tenant_id,
                sequence=self._sequence,
            )
            self._orders[book_order.order_id] = book_order

            # Ensure book exists
            if order.symbol not in self._books:
                self._books[order.symbol] = {"bids": [], "asks": []}

            fills = self._match_order(book_order)

            # If the order has remaining quantity, rest it on the book
            if book_order.remaining > 0 and not book_order.cancelled:
                book = self._books[order.symbol]
                if book_order.side == OrderSide.BUY:
                    entry = _HeapEntry(key=book_order.bid_key(), order=book_order)
                    heapq.heappush(book["bids"], entry)
                else:
                    entry = _HeapEntry(key=book_order.ask_key(), order=book_order)
                    heapq.heappush(book["asks"], entry)

                logger.info(
                    "matching.order_resting",
                    order_id=str(book_order.order_id),
                    symbol=book_order.symbol,
                    side=book_order.side.value,
                    price=str(book_order.price),
                    remaining=str(book_order.remaining),
                )

            return fills

    def cancel_order(self, order_id: UUID) -> bool:
        """Cancel an order by marking it as cancelled.

        The order remains in the heap but will be skipped during matching
        (lazy deletion).  Returns ``True`` if the order was found and
        cancelled, ``False`` otherwise.
        """
        with self._lock:
            book_order = self._orders.get(order_id)
            if book_order is None or book_order.cancelled:
                return False
            book_order.cancelled = True
            logger.info("matching.order_cancelled", order_id=str(order_id))
            return True

    def get_order_book(self, symbol: str) -> dict[str, list[dict[str, str]]]:
        """Return a snapshot of the order book for *symbol*.

        Cancelled and fully filled orders are excluded.
        """
        with self._lock:
            book = self._books.get(symbol, {"bids": [], "asks": []})

            def _side_snapshot(entries: list[_HeapEntry]) -> list[dict[str, str]]:
                result: list[dict[str, str]] = []
                for entry in entries:
                    o = entry.order
                    if o.cancelled or o.remaining <= 0:
                        continue
                    result.append({
                        "order_id": str(o.order_id),
                        "price": str(o.price),
                        "remaining": str(o.remaining),
                        "side": o.side.value,
                    })
                return result

            bids = _side_snapshot(book["bids"])
            asks = _side_snapshot(book["asks"])

            # Sort for display: bids descending, asks ascending
            bids.sort(key=lambda x: Decimal(x["price"]), reverse=True)
            asks.sort(key=lambda x: Decimal(x["price"]))

            return {"bids": bids, "asks": asks}

    def match_orders(self, symbol: str) -> list[OrderFill]:
        """Explicitly trigger matching on *symbol*'s book.

        Normally matching happens automatically in :meth:`add_order`;
        this method is useful for forced re-matching (e.g. after external
        price updates).
        """
        with self._lock:
            book = self._books.get(symbol)
            if book is None:
                return []
            return self._cross_book(symbol)

    # -- internal matching logic ---------------------------------------------

    def _match_order(self, incoming: BookOrder) -> list[OrderFill]:
        """Try to fill *incoming* against the opposite side of the book."""
        book = self._books[incoming.symbol]
        fills: list[OrderFill] = []

        if incoming.side == OrderSide.BUY:
            opposite_heap = book["asks"]
            fills = self._match_against_heap(incoming, opposite_heap, is_buy=True)
        else:
            opposite_heap = book["bids"]
            fills = self._match_against_heap(incoming, opposite_heap, is_buy=False)

        return fills

    def _match_against_heap(
        self,
        incoming: BookOrder,
        opposite: list[_HeapEntry],
        *,
        is_buy: bool,
    ) -> list[OrderFill]:
        """Walk the opposite heap and match while prices cross."""
        fills: list[OrderFill] = []

        while incoming.remaining > 0 and opposite:
            # Peek at the best resting order
            best_entry = opposite[0]
            resting = best_entry.order

            # Skip cancelled / fully filled (lazy deletion)
            if resting.cancelled or resting.remaining <= 0:
                heapq.heappop(opposite)
                continue

            # Price crossing check
            if is_buy:
                # Buyer willing to pay >= ask price, or market order
                if incoming.price > 0 and incoming.price < resting.price:
                    break  # no more matches possible
            else:
                # Seller willing to accept <= bid price, or market order
                if incoming.price > 0 and incoming.price > resting.price:
                    break

            # Determine fill quantity and price
            fill_qty = min(incoming.remaining, resting.remaining)
            fill_price = resting.price  # price-time priority: resting order's price

            # Update quantities
            incoming.remaining -= fill_qty
            resting.remaining -= fill_qty

            # Remove fully filled resting orders from the heap
            if resting.remaining <= 0:
                heapq.heappop(opposite)

            # Determine statuses
            incoming_cumulative = incoming.quantity - incoming.remaining
            incoming_status = (
                OrderStatusEnum.FILLED
                if incoming.remaining == 0
                else OrderStatusEnum.PARTIALLY_FILLED
            )
            resting_cumulative = resting.quantity - resting.remaining
            resting_status = (
                OrderStatusEnum.FILLED
                if resting.remaining == 0
                else OrderStatusEnum.PARTIALLY_FILLED
            )

            # Emit fill for incoming order
            incoming_fill = OrderFill(
                fill_id=uuid4(),
                order_id=incoming.order_id,
                symbol=incoming.symbol,
                side=incoming.side,
                qty=incoming.quantity,
                price=fill_price,
                order_type=OrderType.LIMIT,
                tenant_id=incoming.tenant_id,
                fill_qty=fill_qty,
                fill_price=fill_price,
                cumulative_qty=incoming_cumulative,
                leaves_qty=incoming.remaining,
                status=incoming_status,
                exchange="INTERNAL",
                timestamp=datetime.now(UTC),
            )
            fills.append(incoming_fill)
            self._emit_fill(incoming_fill)

            # Emit fill for resting order
            resting_fill = OrderFill(
                fill_id=uuid4(),
                order_id=resting.order_id,
                symbol=resting.symbol,
                side=resting.side,
                qty=resting.quantity,
                price=fill_price,
                order_type=OrderType.LIMIT,
                tenant_id=resting.tenant_id,
                fill_qty=fill_qty,
                fill_price=fill_price,
                cumulative_qty=resting_cumulative,
                leaves_qty=resting.remaining,
                status=resting_status,
                exchange="INTERNAL",
                timestamp=datetime.now(UTC),
            )
            self._emit_fill(resting_fill)

            logger.info(
                "matching.trade",
                symbol=incoming.symbol,
                price=str(fill_price),
                qty=str(fill_qty),
                buyer=str(incoming.order_id if is_buy else resting.order_id),
                seller=str(resting.order_id if is_buy else incoming.order_id),
            )

        return fills

    def _cross_book(self, symbol: str) -> list[OrderFill]:
        """Walk both sides and match any crossed orders."""
        book = self._books[symbol]
        bids = book["bids"]
        asks = book["asks"]
        fills: list[OrderFill] = []

        while bids and asks:
            # Clean up stale entries
            while bids and (bids[0].order.cancelled or bids[0].order.remaining <= 0):
                heapq.heappop(bids)
            while asks and (asks[0].order.cancelled or asks[0].order.remaining <= 0):
                heapq.heappop(asks)

            if not bids or not asks:
                break

            best_bid = bids[0].order
            best_ask = asks[0].order

            # Check if prices cross (bid price >= ask price)
            if best_bid.price < best_ask.price:
                break

            fill_qty = min(best_bid.remaining, best_ask.remaining)
            fill_price = best_ask.price  # aggressor pays resting price

            best_bid.remaining -= fill_qty
            best_ask.remaining -= fill_qty

            if best_bid.remaining <= 0:
                heapq.heappop(bids)
            if best_ask.remaining <= 0:
                heapq.heappop(asks)

            bid_cumulative = best_bid.quantity - best_bid.remaining
            ask_cumulative = best_ask.quantity - best_ask.remaining

            bid_fill = OrderFill(
                fill_id=uuid4(),
                order_id=best_bid.order_id,
                symbol=symbol,
                side=OrderSide.BUY,
                qty=best_bid.quantity,
                price=fill_price,
                order_type=OrderType.LIMIT,
                tenant_id=best_bid.tenant_id,
                fill_qty=fill_qty,
                fill_price=fill_price,
                cumulative_qty=bid_cumulative,
                leaves_qty=best_bid.remaining,
                status=OrderStatusEnum.FILLED if best_bid.remaining == 0 else OrderStatusEnum.PARTIALLY_FILLED,
                exchange="INTERNAL",
                timestamp=datetime.now(UTC),
            )
            ask_fill = OrderFill(
                fill_id=uuid4(),
                order_id=best_ask.order_id,
                symbol=symbol,
                side=OrderSide.SELL,
                qty=best_ask.quantity,
                price=fill_price,
                order_type=OrderType.LIMIT,
                tenant_id=best_ask.tenant_id,
                fill_qty=fill_qty,
                fill_price=fill_price,
                cumulative_qty=ask_cumulative,
                leaves_qty=best_ask.remaining,
                status=OrderStatusEnum.FILLED if best_ask.remaining == 0 else OrderStatusEnum.PARTIALLY_FILLED,
                exchange="INTERNAL",
                timestamp=datetime.now(UTC),
            )

            fills.extend([bid_fill, ask_fill])
            self._emit_fill(bid_fill)
            self._emit_fill(ask_fill)

            logger.info(
                "matching.cross_trade",
                symbol=symbol,
                price=str(fill_price),
                qty=str(fill_qty),
                buyer=str(best_bid.order_id),
                seller=str(best_ask.order_id),
            )

        return fills

    def _emit_fill(self, fill: OrderFill) -> None:
        """Invoke the fill callback if registered."""
        if self._on_fill is not None:
            try:
                self._on_fill(fill)
            except Exception:
                logger.exception("matching.on_fill_error", fill_id=str(fill.fill_id))


__all__ = [
    "BookOrder",
    "TradeMatchingEngine",
]
