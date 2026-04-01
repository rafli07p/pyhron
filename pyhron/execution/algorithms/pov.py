"""Percentage of Volume (POV) execution algorithm.

Participates at a target rate of real-time volume, with safeguards
for OJK single-investor dominance thresholds.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from pyhron.execution.algorithms.base import (
    ChildOrder,
    ExecutionAlgorithm,
    IDXLotSizeValidator,
    MarketContext,
    Order,
)
from shared.platform_exception_hierarchy import RiskError


class PyhronRiskError(RiskError):
    """Risk limit breached during execution algorithm scheduling."""


_WIB = timezone(timedelta(hours=7))

# OJK single-investor dominance threshold
_OJK_MAX_DAILY_PARTICIPATION = 0.25


class POVAlgorithm(ExecutionAlgorithm):
    """Percentage of Volume execution algorithm.

    Parameters
    ----------
    participation_rate:
        Target fraction of real-time volume to participate (e.g. 0.05 = 5%).
    max_pct_adv:
        Maximum fraction of ADV20 per child order (default 0.10 = 10%).
    num_intervals:
        Number of intervals to simulate participation across.
    """

    def __init__(
        self,
        participation_rate: float = 0.05,
        max_pct_adv: float = 0.10,
        num_intervals: int = 10,
    ) -> None:
        if not 0 < participation_rate <= 1.0:
            msg = "participation_rate must be in (0, 1.0]"
            raise ValueError(msg)
        self._participation_rate = participation_rate
        self._max_pct_adv = max_pct_adv
        self._num_intervals = num_intervals

    def schedule(
        self,
        order: Order,
        market_context: MarketContext,
    ) -> list[ChildOrder]:
        lot_size = market_context.lot_size
        total_qty = order.quantity
        adv = market_context.adv_20d

        # Estimate volume per interval based on ADV
        estimated_daily_volume = adv
        volume_per_interval = estimated_daily_volume / self._num_intervals

        # Check OJK dominance threshold
        total_participation = total_qty / estimated_daily_volume if estimated_daily_volume > 0 else 1.0
        if total_participation > _OJK_MAX_DAILY_PARTICIPATION:
            raise PyhronRiskError(
                f"Total order quantity ({total_qty}) exceeds OJK 25% daily "
                f"volume threshold ({_OJK_MAX_DAILY_PARTICIPATION * 100}% of "
                f"ADV={estimated_daily_volume:.0f}). "
                f"Participation would be {total_participation * 100:.1f}%."
            )

        # Max shares per child order
        max_child_qty = int(adv * self._max_pct_adv)

        now = datetime.now(tz=_WIB)
        interval_minutes = max(1, market_context.session_remaining_minutes // self._num_intervals)

        children: list[ChildOrder] = []
        allocated = 0

        for i in range(self._num_intervals):
            if allocated >= total_qty:
                break

            # Simulate observed volume for this interval
            raw_qty = int(volume_per_interval * self._participation_rate)
            raw_qty = min(raw_qty, max_child_qty)
            raw_qty = min(raw_qty, total_qty - allocated)

            qty = IDXLotSizeValidator.snap_to_lot_floor(raw_qty, lot_size)
            if qty <= 0:
                continue

            sched_time = now + timedelta(minutes=i * interval_minutes)

            allocated += qty
            children.append(
                ChildOrder(
                    symbol=order.symbol,
                    quantity=qty,
                    limit_price=None,
                    scheduled_time=sched_time,
                    algo_tag="POV",
                )
            )

        return sorted(children, key=lambda c: c.scheduled_time)
