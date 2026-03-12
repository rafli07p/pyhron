"""Order Book Panel for the Enthropy Terminal.

Displays a live, depth-sorted order book with real-time bid/ask updates.
Connects to the DataClient for streaming quote and depth data.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class PriceLevel:
    """A single price level in the order book."""

    price: Decimal
    size: Decimal
    order_count: int = 1
    timestamp: datetime | None = None


@dataclass
class OrderBookState:
    """Current state of the order book for a symbol."""

    symbol: str = ""
    bids: list[PriceLevel] = field(default_factory=list)
    asks: list[PriceLevel] = field(default_factory=list)
    last_update: datetime | None = None
    sequence: int = 0


class OrderBookPanel:
    """Display a live order book with depth visualization.

    Shows real-time bids and asks sorted by price, with size aggregation
    at each price level. Subscribes to streaming depth data through the
    terminal's DataClient.

    Parameters
    ----------
    data_client:
        Instance of ``apps.terminal.data_client.DataClient`` for market
        data subscriptions. If ``None``, operates in offline mode.
    max_depth:
        Maximum number of price levels to display per side.
    """

    def __init__(self, data_client: Any = None, max_depth: int = 20) -> None:
        self._data_client = data_client
        self._max_depth = max_depth
        self._state = OrderBookState()
        self._subscriptions: set[str] = set()
        logger.info("OrderBookPanel initialized (max_depth=%d)", max_depth)

    @property
    def symbol(self) -> str:
        """Currently displayed symbol."""
        return self._state.symbol

    @property
    def spread(self) -> Decimal | None:
        """Current bid-ask spread, or ``None`` if the book is empty."""
        if self._state.bids and self._state.asks:
            return self._state.asks[0].price - self._state.bids[0].price
        return None

    async def render_orderbook(self, symbol: str) -> dict[str, Any]:
        """Render the order book for a given symbol.

        Fetches the current book snapshot from the data client and
        returns a structured representation for display.

        Parameters
        ----------
        symbol:
            Instrument symbol (e.g., ``AAPL``, ``BBCA.JK``).

        Returns
        -------
        dict[str, Any]
            Order book payload with bids, asks, spread, and metadata.
        """
        self._state.symbol = symbol

        if self._data_client is not None:
            snapshot = await self._data_client.get_market_data(
                symbol=symbol,
                data_type="orderbook",
            )
            if isinstance(snapshot, dict):
                self._parse_snapshot(snapshot)

        if symbol not in self._subscriptions and self._data_client is not None:
            await self._data_client.subscribe_realtime(
                symbol=symbol,
                channel="orderbook",
                callback=self._on_book_update,
            )
            self._subscriptions.add(symbol)

        self._state.last_update = datetime.utcnow()
        logger.info(
            "Rendered order book for %s (%d bids, %d asks)", symbol, len(self._state.bids), len(self._state.asks)
        )

        return self._serialize_book()

    def update_bids_asks(
        self,
        bids: list[tuple[Decimal, Decimal]],
        asks: list[tuple[Decimal, Decimal]],
    ) -> None:
        """Manually update the order book bids and asks.

        Parameters
        ----------
        bids:
            List of ``(price, size)`` tuples sorted descending by price.
        asks:
            List of ``(price, size)`` tuples sorted ascending by price.
        """
        self._state.bids = [PriceLevel(price=p, size=s) for p, s in bids[: self._max_depth]]
        self._state.asks = [PriceLevel(price=p, size=s) for p, s in asks[: self._max_depth]]
        self._state.last_update = datetime.utcnow()
        self._state.sequence += 1

    def get_depth(self, levels: int = 10) -> dict[str, Any]:
        """Return aggregated depth for the top N price levels.

        Parameters
        ----------
        levels:
            Number of levels per side to include.

        Returns
        -------
        dict[str, Any]
            Aggregated depth with cumulative sizes.
        """
        bid_depth: list[dict[str, Any]] = []
        cumulative = Decimal("0")
        for lvl in self._state.bids[:levels]:
            cumulative += lvl.size
            bid_depth.append({"price": str(lvl.price), "size": str(lvl.size), "cumulative": str(cumulative)})

        ask_depth: list[dict[str, Any]] = []
        cumulative = Decimal("0")
        for lvl in self._state.asks[:levels]:
            cumulative += lvl.size
            ask_depth.append({"price": str(lvl.price), "size": str(lvl.size), "cumulative": str(cumulative)})

        return {
            "symbol": self._state.symbol,
            "bid_depth": bid_depth,
            "ask_depth": ask_depth,
            "spread": str(self.spread) if self.spread is not None else None,
        }

    def _parse_snapshot(self, snapshot: dict[str, Any]) -> None:
        """Parse a raw order book snapshot from the data client."""
        raw_bids = snapshot.get("bids", [])
        raw_asks = snapshot.get("asks", [])
        self._state.bids = [
            PriceLevel(price=Decimal(str(b[0])), size=Decimal(str(b[1]))) for b in raw_bids[: self._max_depth]
        ]
        self._state.asks = [
            PriceLevel(price=Decimal(str(a[0])), size=Decimal(str(a[1]))) for a in raw_asks[: self._max_depth]
        ]

    async def _on_book_update(self, update: dict[str, Any]) -> None:
        """Handle a streaming order book update."""
        if "bids" in update or "asks" in update:
            self._parse_snapshot(update)
            self._state.last_update = datetime.utcnow()
            self._state.sequence += 1

    def _serialize_book(self) -> dict[str, Any]:
        """Serialize current book state for rendering."""
        return {
            "symbol": self._state.symbol,
            "bids": [{"price": str(l.price), "size": str(l.size)} for l in self._state.bids],
            "asks": [{"price": str(l.price), "size": str(l.size)} for l in self._state.asks],
            "spread": str(self.spread) if self.spread is not None else None,
            "bid_levels": len(self._state.bids),
            "ask_levels": len(self._state.asks),
            "sequence": self._state.sequence,
            "last_update": self._state.last_update.isoformat() if self._state.last_update else None,
        }


__all__ = [
    "OrderBookPanel",
    "OrderBookState",
    "PriceLevel",
]
