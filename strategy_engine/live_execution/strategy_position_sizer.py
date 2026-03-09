"""Kelly fraction position sizing for live strategy execution.

Implements the Kelly Criterion with fractional scaling to determine
optimal position sizes given signal confidence and expected return
distributions, subject to IDX lot-size constraints.

References:
    Kelly (1956) — *A New Interpretation of Information Rate*.
    Thorp (2006) — *The Kelly Criterion in Blackjack, Sports Betting,
    and the Stock Market*.

Usage::

    sizer = StrategyPositionSizer(max_kelly_fraction=0.25)
    sized = sizer.size_positions(signals, portfolio_value, prices)
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from shared.structured_json_logger import get_logger

if TYPE_CHECKING:
    from strategy_engine.base_strategy_interface import StrategySignal

logger = get_logger(__name__)

_IDX_LOT_SIZE: int = 100


@dataclass(frozen=True)
class SizedPosition:
    """Position size recommendation for a single signal.

    Attributes:
        symbol: Ticker symbol.
        signal: Original strategy signal.
        kelly_fraction: Raw Kelly fraction.
        scaled_fraction: Kelly fraction after scaling.
        target_shares: Number of shares (lot-rounded).
        target_value_idr: Position value in IDR.
        portfolio_weight: Fraction of portfolio value.
    """

    symbol: str
    signal: StrategySignal
    kelly_fraction: float
    scaled_fraction: float
    target_shares: int
    target_value_idr: float
    portfolio_weight: float


class StrategyPositionSizer:
    """Kelly-criterion position sizer with IDX lot-size constraints.

    Computes the Kelly fraction for each signal based on confidence
    and expected win/loss ratio, then scales down by ``kelly_scale``
    to reduce variance (fractional Kelly).

    Args:
        kelly_scale: Fraction of full Kelly to use (default 0.25 = quarter Kelly).
        max_position_pct: Maximum single-position weight (default 10%).
        max_portfolio_heat: Maximum total portfolio allocation (default 95%).
        expected_win_loss_ratio: Assumed average win/loss ratio.
        lot_size: IDX lot size (default 100).
    """

    def __init__(
        self,
        kelly_scale: float = 0.25,
        max_position_pct: float = 0.10,
        max_portfolio_heat: float = 0.95,
        expected_win_loss_ratio: float = 1.5,
        lot_size: int = _IDX_LOT_SIZE,
    ) -> None:
        self._kelly_scale = kelly_scale
        self._max_position_pct = max_position_pct
        self._max_portfolio_heat = max_portfolio_heat
        self._win_loss_ratio = expected_win_loss_ratio
        self._lot_size = lot_size

        logger.info(
            "position_sizer_initialised",
            kelly_scale=kelly_scale,
            max_position_pct=max_position_pct,
            max_portfolio_heat=max_portfolio_heat,
        )

    def compute_kelly_fraction(self, confidence: float) -> float:
        """Compute Kelly fraction from signal confidence.

        Kelly formula: f* = p - (1 - p) / b
        where p = win probability (confidence), b = win/loss ratio.

        Args:
            confidence: Signal confidence in [0, 1] as win probability.

        Returns:
            Kelly fraction (may be negative if edge is insufficient).
        """
        p = max(0.0, min(1.0, confidence))
        q = 1.0 - p
        b = self._win_loss_ratio

        if b <= 0:
            return 0.0
        kelly = p - q / b
        return max(0.0, kelly)

    def size_positions(
        self,
        signals: list[StrategySignal],
        portfolio_value: float,
        current_prices: dict[str, float],
    ) -> list[SizedPosition]:
        """Size positions for a batch of signals.

        Steps:
            1. Compute Kelly fraction per signal.
            2. Scale by ``kelly_scale`` (fractional Kelly).
            3. Cap individual positions at ``max_position_pct``.
            4. Normalise if total exceeds ``max_portfolio_heat``.
            5. Round shares to lot size.

        Args:
            signals: List of strategy signals to size.
            portfolio_value: Current portfolio value in IDR.
            current_prices: Mapping of symbol to current price in IDR.

        Returns:
            List of SizedPosition with lot-rounded share counts.
        """
        if not signals or portfolio_value <= 0:
            return []

        raw_positions: list[tuple[StrategySignal, float]] = []
        for sig in signals:
            kelly = self.compute_kelly_fraction(sig.confidence)
            scaled = kelly * self._kelly_scale
            capped = min(scaled, self._max_position_pct)
            raw_positions.append((sig, capped))

        # Normalise if total exceeds portfolio heat limit.
        total_weight = sum(w for _, w in raw_positions)
        if total_weight > self._max_portfolio_heat:
            scale_factor = self._max_portfolio_heat / total_weight
            raw_positions = [(s, w * scale_factor) for s, w in raw_positions]

        sized: list[SizedPosition] = []
        for sig, weight in raw_positions:
            price = current_prices.get(sig.symbol, 0.0)
            if price <= 0 or weight <= 0:
                continue

            target_value = portfolio_value * weight
            raw_shares = int(target_value / price)
            lot_shares = (raw_shares // self._lot_size) * self._lot_size

            if lot_shares <= 0:
                continue

            actual_value = lot_shares * price
            actual_weight = actual_value / portfolio_value

            sized.append(
                SizedPosition(
                    symbol=sig.symbol,
                    signal=sig,
                    kelly_fraction=self.compute_kelly_fraction(sig.confidence),
                    scaled_fraction=weight,
                    target_shares=lot_shares,
                    target_value_idr=actual_value,
                    portfolio_weight=round(actual_weight, 6),
                )
            )

        logger.info(
            "positions_sized",
            num_signals=len(signals),
            num_positions=len(sized),
            total_weight=round(sum(p.portfolio_weight for p in sized), 4),
        )
        return sized
