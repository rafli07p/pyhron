"""Volume-Weighted Average Price (VWAP) execution algorithm.

Distributes a parent order across time buckets proportional to
historical or default intraday volume profiles.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import TYPE_CHECKING

from pyhron.execution.algorithms.base import (
    ChildOrder,
    ExecutionAlgorithm,
    IDXLotSizeValidator,
    MarketContext,
    Order,
)

if TYPE_CHECKING:
    import pandas as pd

# IDX default V-curve volume distribution
# 09:00-10:00 → 35%, 10:00-11:30 → 30%, 13:30-14:30 → 20%, 14:30-15:00 → 15%
_WIB = timezone(timedelta(hours=7))

_IDX_DEFAULT_PROFILE: dict[int, float] = {}

# 09:00-10:00 (60 min): 35% → each minute gets 35/60
for m in range(9 * 60, 10 * 60):
    _IDX_DEFAULT_PROFILE[m] = 0.35 / 60

# 10:00-11:30 (90 min): 30%
for m in range(10 * 60, 11 * 60 + 30):
    _IDX_DEFAULT_PROFILE[m] = 0.30 / 90

# 13:30-14:30 (60 min): 20%
for m in range(13 * 60 + 30, 14 * 60 + 30):
    _IDX_DEFAULT_PROFILE[m] = 0.20 / 60

# 14:30-15:00 (30 min): 15%
for m in range(14 * 60 + 30, 15 * 60):
    _IDX_DEFAULT_PROFILE[m] = 0.15 / 30


def _minute_of_day(dt: datetime) -> int:
    wib = dt.astimezone(_WIB)
    return wib.hour * 60 + wib.minute


class VWAPAlgorithm(ExecutionAlgorithm):
    """Volume-Weighted Average Price execution algorithm.

    Parameters
    ----------
    volume_profile:
        Mapping of minute_of_day → volume fraction.  Must sum to 1.0 ± 1e-6.
        If ``None``, uses the IDX default V-curve.
    num_buckets:
        Number of time buckets to group volume into.
    """

    def __init__(
        self,
        volume_profile: dict[int, float] | None = None,
        num_buckets: int = 20,
    ) -> None:
        if volume_profile is not None:
            total = sum(volume_profile.values())
            if abs(total - 1.0) > 1e-6:
                msg = f"Volume profile fractions must sum to 1.0 (got {total})"
                raise ValueError(msg)
            self._profile = volume_profile
        else:
            self._profile = _IDX_DEFAULT_PROFILE
        self._num_buckets = num_buckets

    @classmethod
    def from_historical(cls, ohlcv_df: pd.DataFrame) -> VWAPAlgorithm:
        """Estimate intraday volume profile from historical minute-bar data.

        Parameters
        ----------
        ohlcv_df:
            DataFrame with DatetimeIndex and a ``volume`` column.

        Returns
        -------
        VWAPAlgorithm
            Configured with the estimated volume profile.
        """
        import pandas as pd

        df = ohlcv_df.copy()
        if not isinstance(df.index, pd.DatetimeIndex):
            msg = "ohlcv_df must have a DatetimeIndex"
            raise TypeError(msg)

        # Convert to WIB if needed
        if df.index.tz is None:
            df.index = df.index.tz_localize("UTC").tz_convert(_WIB)
        else:
            df.index = df.index.tz_convert(_WIB)

        df["minute_of_day"] = df.index.hour * 60 + df.index.minute
        avg_volume = df.groupby("minute_of_day")["volume"].mean()
        total_vol = avg_volume.sum()
        if total_vol == 0:
            return cls()
        profile = (avg_volume / total_vol).to_dict()
        return cls(volume_profile=profile)

    def schedule(
        self,
        order: Order,
        market_context: MarketContext,
    ) -> list[ChildOrder]:
        lot_size = market_context.lot_size
        total_qty = order.quantity

        now = datetime.now(tz=_WIB)
        current_minute = _minute_of_day(now)

        # Filter profile to remaining trading minutes
        remaining_profile = {m: v for m, v in self._profile.items() if m >= current_minute}

        if not remaining_profile:
            return []

        # Normalise remaining profile
        total_fraction = sum(remaining_profile.values())
        if total_fraction == 0:
            return []

        normalized = {m: v / total_fraction for m, v in remaining_profile.items()}

        # Group into buckets
        sorted_minutes = sorted(normalized.keys())
        bucket_size = max(1, len(sorted_minutes) // self._num_buckets)
        buckets: list[tuple[int, float]] = []

        for i in range(0, len(sorted_minutes), bucket_size):
            chunk = sorted_minutes[i : i + bucket_size]
            fraction = sum(normalized[m] for m in chunk)
            buckets.append((chunk[0], fraction))

        # Allocate quantities proportional to bucket fractions
        children: list[ChildOrder] = []
        allocated = 0
        rounding_error = 0.0

        for i, (minute, fraction) in enumerate(buckets):
            raw_qty = total_qty * fraction + rounding_error
            qty = IDXLotSizeValidator.snap_to_lot_floor(int(raw_qty), lot_size)
            rounding_error = raw_qty - qty

            if i == len(buckets) - 1:
                # Final bucket: flush rounding remainder
                qty = total_qty - allocated
                qty = IDXLotSizeValidator.snap_to_lot_floor(qty, lot_size)

            if qty <= 0:
                continue

            # Build scheduled time
            today = now.replace(hour=0, minute=0, second=0, microsecond=0)
            sched_time = today + timedelta(minutes=minute)

            allocated += qty
            children.append(
                ChildOrder(
                    symbol=order.symbol,
                    quantity=qty,
                    limit_price=None,
                    scheduled_time=sched_time,
                    algo_tag="VWAP",
                )
            )

        return sorted(children, key=lambda c: c.scheduled_time)
