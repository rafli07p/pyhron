from __future__ import annotations

from decimal import Decimal


class MeanReversionStrategy:
    def __init__(
        self,
        lookback_period: int,
        entry_z_score: Decimal,
        exit_z_score: Decimal,
        position_size_pct: Decimal,
    ) -> None:
        self._lookback_period = lookback_period
        self._entry_z_score = entry_z_score
        self._exit_z_score = exit_z_score
        self._position_size_pct = position_size_pct

    @property
    def name(self) -> str:
        return "MeanReversionStrategy"

    @property
    def parameters(self) -> dict:
        return {
            "lookback_period": self._lookback_period,
            "entry_z_score": self._entry_z_score,
            "exit_z_score": self._exit_z_score,
            "position_size_pct": self._position_size_pct,
        }
