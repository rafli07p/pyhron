"""Time-Weighted Average Price (TWAP) execution algorithm.

Slices a parent order into N equal time buckets across the remaining
trading session, respecting IDX session breaks (11:30-13:30 WIB).
"""

from __future__ import annotations

import random
from datetime import datetime, timedelta, timezone

from pyhron.execution.algorithms.base import (
    ChildOrder,
    ExecutionAlgorithm,
    IDXLotSizeValidator,
    MarketContext,
    Order,
)

# IDX sessions in WIB (UTC+7)
_WIB = timezone(timedelta(hours=7))
_SESSION1_START_MINUTE = 9 * 60  # 09:00
_SESSION1_END_MINUTE = 11 * 60 + 30  # 11:30
_SESSION2_START_MINUTE = 13 * 60 + 30  # 13:30
_SESSION2_END_MINUTE = 15 * 60  # 15:00


def _minute_of_day(dt: datetime) -> int:
    wib = dt.astimezone(_WIB)
    return wib.hour * 60 + wib.minute


def _is_in_trading_session(minute: int) -> bool:
    return (
        _SESSION1_START_MINUTE <= minute < _SESSION1_END_MINUTE
        or _SESSION2_START_MINUTE <= minute < _SESSION2_END_MINUTE
    )


class TWAPAlgorithm(ExecutionAlgorithm):
    """Time-Weighted Average Price execution algorithm.

    Parameters
    ----------
    num_slices:
        Number of child order slices to create.
    randomize_pct:
        Anti-gaming jitter (0.0-0.2) applied to scheduled times.
    """

    def __init__(self, num_slices: int = 10, randomize_pct: float = 0.0) -> None:
        if num_slices < 1:
            msg = "num_slices must be >= 1"
            raise ValueError(msg)
        if not 0.0 <= randomize_pct <= 0.2:
            msg = "randomize_pct must be between 0.0 and 0.2"
            raise ValueError(msg)
        self._num_slices = num_slices
        self._randomize_pct = randomize_pct

    def schedule(
        self,
        order: Order,
        market_context: MarketContext,
    ) -> list[ChildOrder]:
        lot_size = market_context.lot_size
        total_qty = order.quantity

        # Generate trading minutes within remaining session
        now = datetime.now(tz=_WIB)
        trading_minutes = self._get_trading_minutes(now, market_context.session_remaining_minutes)

        if not trading_minutes:
            return []

        # Distribute slices evenly across trading minutes
        n = min(self._num_slices, len(trading_minutes))
        step = max(1, len(trading_minutes) // n)
        slice_times = [trading_minutes[min(i * step, len(trading_minutes) - 1)] for i in range(n)]

        # Compute per-slice quantity
        base_qty = IDXLotSizeValidator.snap_to_lot_floor(total_qty // n, lot_size)
        children: list[ChildOrder] = []
        allocated = 0

        for i, sched_time in enumerate(slice_times):
            if i == len(slice_times) - 1:
                # Final slice gets the remainder
                qty = total_qty - allocated
            else:
                qty = base_qty

            qty = IDXLotSizeValidator.snap_to_lot_floor(qty, lot_size)
            if qty <= 0:
                continue

            # Apply jitter
            if self._randomize_pct > 0 and i < len(slice_times) - 1:
                max_jitter = int(step * self._randomize_pct)
                jitter_minutes = random.randint(-max_jitter, max_jitter)
                sched_time = sched_time + timedelta(minutes=jitter_minutes)

            allocated += qty
            children.append(
                ChildOrder(
                    symbol=order.symbol,
                    quantity=qty,
                    limit_price=None,
                    scheduled_time=sched_time,
                    algo_tag="TWAP",
                )
            )

        return sorted(children, key=lambda c: c.scheduled_time)

    @staticmethod
    def _get_trading_minutes(now: datetime, remaining_minutes: int) -> list[datetime]:
        """Generate a list of datetimes for each trading minute remaining."""
        minutes: list[datetime] = []
        current = now.replace(second=0, microsecond=0)

        for i in range(remaining_minutes):
            candidate = current + timedelta(minutes=i)
            mod = _minute_of_day(candidate)
            if _is_in_trading_session(mod):
                minutes.append(candidate)

        return minutes
