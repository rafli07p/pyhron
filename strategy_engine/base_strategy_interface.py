"""Abstract base class for all Pyhron trading strategies.

Every strategy — whether momentum, mean-reversion, or factor-based — must
implement this interface so the engine can drive them uniformly.

Usage::

    from strategy_engine.base_strategy_interface import BaseStrategyInterface

    class MyStrategy(BaseStrategyInterface):
        ...
"""

from __future__ import annotations

import abc
from dataclasses import dataclass, field
from enum import StrEnum
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from datetime import datetime

    import pandas as pd

# ── Supporting Types ─────────────────────────────────────────────────────────


class SignalDirection(StrEnum):
    """Direction of a trading signal."""

    LONG = "LONG"
    SHORT = "SHORT"
    CLOSE = "CLOSE"
    REBALANCE = "REBALANCE"


@dataclass(frozen=True)
class StrategySignal:
    """Immutable value object representing a single trading signal.

    Attributes:
        symbol: Ticker symbol (e.g. ``BBCA``).
        direction: Long, short, close, or rebalance.
        target_weight: Desired portfolio weight in ``[0, 1]``.
        confidence: Model confidence in ``[0, 1]``.
        strategy_id: Unique strategy identifier.
        generated_at: UTC timestamp when the signal was created.
        metadata: Arbitrary key-value pairs for factor values, scores, etc.
    """

    symbol: str
    direction: SignalDirection
    target_weight: float
    confidence: float
    strategy_id: str
    generated_at: datetime
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class StrategyParameters:
    """Container for strategy hyper-parameters.

    Attributes:
        name: Human-readable strategy name.
        version: Semantic version string.
        universe: List of symbols the strategy trades.
        lookback_days: Number of calendar days of historical data required.
        rebalance_frequency: How often the strategy rebalances (e.g. ``monthly``).
        custom: Strategy-specific parameters.
    """

    name: str
    version: str
    universe: list[str]
    lookback_days: int
    rebalance_frequency: str
    custom: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class BarData:
    """OHLCV bar for a single symbol.

    Attributes:
        symbol: Ticker symbol.
        timestamp: Bar timestamp (UTC).
        open: Opening price.
        high: High price.
        low: Low price.
        close: Closing price.
        volume: Volume traded.
    """

    symbol: str
    timestamp: datetime
    open: float
    high: float
    low: float
    close: float
    volume: int


@dataclass(frozen=True)
class TickData:
    """Single tick (trade or quote) for a symbol.

    Attributes:
        symbol: Ticker symbol.
        timestamp: Tick timestamp (UTC).
        price: Last-traded or quote price.
        volume: Tick volume.
        bid: Best bid price (optional).
        ask: Best ask price (optional).
    """

    symbol: str
    timestamp: datetime
    price: float
    volume: int
    bid: float | None = None
    ask: float | None = None


# ── Abstract Base Strategy ───────────────────────────────────────────────────


class BaseStrategyInterface(abc.ABC):
    """Abstract base class that every Pyhron strategy must implement.

    Lifecycle::

        1. Engine calls ``get_parameters`` to discover universe, lookback, etc.
        2. Engine feeds historical bars via ``on_bar`` (warm-up phase).
        3. Engine calls ``generate_signals`` on each rebalance date.
        4. In live mode, ``on_tick`` is called for real-time data.

    Subclasses **must** implement all four abstract methods.
    """

    @abc.abstractmethod
    async def generate_signals(
        self,
        market_data: pd.DataFrame,
        as_of_date: datetime,
    ) -> list[StrategySignal]:
        """Produce trading signals given current market state.

        Args:
            market_data: DataFrame with multi-index ``(date, symbol)`` and
                columns ``open, high, low, close, volume`` (at minimum).
            as_of_date: The evaluation date (no look-ahead beyond this).

        Returns:
            A list of ``StrategySignal`` objects — may be empty if the
            strategy has no actionable view.
        """

    @abc.abstractmethod
    def get_parameters(self) -> StrategyParameters:
        """Return the strategy's current parameters.

        Returns:
            A ``StrategyParameters`` instance describing name, universe,
            lookback, rebalance frequency, and custom hyper-parameters.
        """

    @abc.abstractmethod
    async def on_bar(self, bar: BarData) -> list[StrategySignal]:
        """React to a new OHLCV bar.

        Called once per bar per symbol during both back-testing and live
        execution.  The strategy may update internal state and optionally
        emit intra-rebalance signals.

        Args:
            bar: A single OHLCV bar.

        Returns:
            A (possibly empty) list of signals.
        """

    @abc.abstractmethod
    async def on_tick(self, tick: TickData) -> list[StrategySignal]:
        """React to a live tick.

        Only called in live-execution mode.  High-frequency strategies
        override this; slower strategies may simply return an empty list.

        Args:
            tick: A single tick event.

        Returns:
            A (possibly empty) list of signals.
        """
