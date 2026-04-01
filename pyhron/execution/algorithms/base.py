"""Base classes for execution algorithms.

Defines the abstract interface that all execution algorithms must implement,
plus shared data structures for child orders and market context.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal


@dataclass(frozen=True)
class ChildOrder:
    """A single slice of a parent order produced by an execution algorithm.

    Attributes
    ----------
    symbol:
        Ticker symbol.
    quantity:
        Number of shares — must be a multiple of ``lot_size`` (default 100).
    limit_price:
        Limit price for the slice, or ``None`` for market order.
    scheduled_time:
        When this slice should be sent to the exchange.
    algo_tag:
        Name of the algorithm that produced this slice.
    """

    symbol: str
    quantity: int
    limit_price: Decimal | None
    scheduled_time: datetime
    algo_tag: str


@dataclass(frozen=True)
class MarketContext:
    """Snapshot of current market state for an instrument.

    Attributes
    ----------
    adv_20d:
        20-day average daily volume (shares).
    bid:
        Current best bid price.
    ask:
        Current best ask price.
    last:
        Last traded price.
    session_remaining_minutes:
        Minutes remaining in the current trading session.
    lot_size:
        IDX lot size (default 100 shares).
    """

    adv_20d: float
    bid: Decimal
    ask: Decimal
    last: Decimal
    session_remaining_minutes: int
    lot_size: int = 100


@dataclass(frozen=True)
class Order:
    """Parent order to be executed by an algorithm.

    Attributes
    ----------
    order_id:
        Unique order identifier.
    symbol:
        Ticker symbol.
    quantity:
        Total shares to execute.
    side:
        ``"BUY"`` or ``"SELL"``.
    """

    order_id: str
    symbol: str
    quantity: int
    side: str


class IDXLotSizeValidator:
    """Utility for snapping quantities to IDX lot-size multiples.

    IDX requires all order quantities to be multiples of 100 shares.
    """

    @staticmethod
    def snap_to_lot(quantity: int, lot_size: int = 100) -> int:
        """Round ``quantity`` down to the nearest ``lot_size`` multiple.

        Raises
        ------
        ValueError
            If the snapped quantity is zero (order too small).
        """
        snapped = (quantity // lot_size) * lot_size
        if snapped <= 0:
            msg = f"Order quantity {quantity} is too small for lot size {lot_size}"
            raise ValueError(msg)
        return snapped

    @staticmethod
    def snap_to_lot_floor(quantity: int, lot_size: int = 100) -> int:
        """Round ``quantity`` down to the nearest lot without raising on zero."""
        return (quantity // lot_size) * lot_size


class ExecutionAlgorithm(ABC):
    """Abstract base class for all execution algorithms."""

    @abstractmethod
    def schedule(
        self,
        order: Order,
        market_context: MarketContext,
    ) -> list[ChildOrder]:
        """Break a parent order into a list of child orders.

        Parameters
        ----------
        order:
            The parent order to slice.
        market_context:
            Current market state.

        Returns
        -------
        list[ChildOrder]
            Child orders sorted by ``scheduled_time``.
        """
        ...
