from __future__ import annotations

from decimal import Decimal


class MomentumStrategy:
    def __init__(
        self,
        lookback_period: int,
        entry_threshold: Decimal,
        exit_threshold: Decimal,
        position_size_pct: Decimal,
    ) -> None:
        self._lookback_period = lookback_period
        self._entry_threshold = entry_threshold
        self._exit_threshold = exit_threshold
        self._position_size_pct = position_size_pct

    @property
    def name(self) -> str:
        return "MomentumStrategy"

    @property
    def parameters(self) -> dict:
        return {
            "lookback_period": self._lookback_period,
            "entry_threshold": self._entry_threshold,
            "exit_threshold": self._exit_threshold,
            "position_size_pct": self._position_size_pct,
        }
