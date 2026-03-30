"""PBV + ROE quarterly rebalance value factor strategy for IDX equities.

Constructs a composite value score from Price-to-Book Value (PBV) and
Return on Equity (ROE), then goes long the cheapest-yet-profitable
stocks on a quarterly rebalance cycle.

References:
    Fama & French (1993) — *Common Risk Factors in the Returns on Stocks*.
    Piotroski (2000) — *Value Investing: The Use of Historical Financial*.

Usage::

    strategy = IDXValueFactorStrategy()
    signals = await strategy.generate_signals(market_data, as_of_date)
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import numpy as np
import pandas as pd

from shared.structured_json_logger import get_logger
from strategy_engine.base_strategy_interface import (
    BarData,
    BaseStrategyInterface,
    SignalDirection,
    StrategyParameters,
    StrategySignal,
    TickData,
)
from strategy_engine.survivorship_filter import filter_tradable_symbols

if TYPE_CHECKING:
    from datetime import datetime

logger = get_logger(__name__)

_DEFAULT_UNIVERSE: list[str] = [
    "BBCA",
    "BBRI",
    "BMRI",
    "BBNI",
    "TLKM",
    "ASII",
    "UNVR",
    "HMSP",
    "GGRM",
    "KLBF",
    "ICBP",
    "INDF",
    "SMGR",
    "PTBA",
    "ADRO",
    "ITMG",
    "UNTR",
    "PGAS",
    "JSMR",
    "CPIN",
    "INKP",
    "INTP",
    "SMRA",
    "BSDE",
    "WIKA",
    "WSKT",
    "ANTM",
    "TINS",
    "INCO",
    "EXCL",
    "TOWR",
    "TBIG",
]


class IDXValueFactorStrategy(BaseStrategyInterface):
    """PBV + ROE composite value factor strategy with quarterly rebalance.

    Scoring formula:
        value_score = z_score(-PBV) + z_score(ROE)
    Stocks with ROE < ``min_roe`` are excluded (value trap filter).
    Top quintile is selected for equal-weight long portfolio.

    Args:
        universe: List of IDX ticker symbols.
        top_quantile: Fraction of universe to go long (default 0.2).
        min_roe: Minimum ROE threshold to exclude value traps.
        pbv_weight: Weight of PBV z-score in composite (default 0.5).
        roe_weight: Weight of ROE z-score in composite (default 0.5).
        strategy_id: Unique strategy identifier.
    """

    def __init__(
        self,
        universe: list[str] | None = None,
        top_quantile: float = 0.20,
        min_roe: float = 0.05,
        pbv_weight: float = 0.5,
        roe_weight: float = 0.5,
        strategy_id: str = "idx_value_pbv_roe",
        instrument_metadata: pd.DataFrame | None = None,
    ) -> None:
        self._universe = universe or list(_DEFAULT_UNIVERSE)
        self._top_quantile = top_quantile
        self._min_roe = min_roe
        self._pbv_weight = pbv_weight
        self._roe_weight = roe_weight
        self._strategy_id = strategy_id
        self._instrument_metadata = instrument_metadata

        logger.info(
            "value_strategy_initialised",
            strategy_id=self._strategy_id,
            universe_size=len(self._universe),
        )

    def get_parameters(self) -> StrategyParameters:
        return StrategyParameters(
            name="IDX PBV+ROE Value Factor",
            version="1.0.0",
            universe=list(self._universe),
            lookback_days=90,
            rebalance_frequency="quarterly",
            custom={
                "top_quantile": self._top_quantile,
                "min_roe": self._min_roe,
                "pbv_weight": self._pbv_weight,
                "roe_weight": self._roe_weight,
            },
        )

    async def generate_signals(self, market_data: pd.DataFrame, as_of_date: datetime) -> list[StrategySignal]:
        """Generate value factor signals from PBV and ROE data.

        ``market_data`` must contain columns ``pbv`` and ``roe`` indexed by
        symbol (or multi-index with date and symbol).

        Args:
            market_data: DataFrame with fundamental data.
            as_of_date: Evaluation date.

        Returns:
            List of StrategySignal for top-quintile value stocks.
        """
        logger.info("value_signal_generation_start", as_of_date=as_of_date.isoformat())
        try:
            return self._compute_value_signals(market_data, as_of_date)
        except (KeyError, ValueError) as exc:
            logger.error("value_signal_generation_failed", error=str(exc))
            return []

    async def on_bar(self, bar: BarData) -> list[StrategySignal]:
        return []

    async def on_tick(self, tick: TickData) -> list[StrategySignal]:
        return []

    def _compute_value_signals(self, market_data: pd.DataFrame, as_of_date: datetime) -> list[StrategySignal]:
        if isinstance(market_data.index, pd.MultiIndex):
            latest = market_data.xs(market_data.index.get_level_values("date").max(), level="date")
        else:
            latest = market_data

        # Survivorship bias filter (M-1)
        universe = filter_tradable_symbols(self._universe, as_of_date, self._instrument_metadata)

        fundamentals = latest[["pbv", "roe"]].copy()
        fundamentals = fundamentals.reindex(universe).dropna()

        # Filter value traps: ROE must exceed minimum threshold.
        fundamentals = fundamentals[fundamentals["roe"] >= self._min_roe]
        if len(fundamentals) < 3:
            logger.warning("value_insufficient_stocks", count=len(fundamentals))
            return []

        # Cross-sectional z-scores.
        pbv_std = fundamentals["pbv"].std()
        roe_std = fundamentals["roe"].std()
        if pbv_std < 1e-6:
            pbv_z = pd.Series(0.0, index=fundamentals.index)
        else:
            pbv_z = -(fundamentals["pbv"] - fundamentals["pbv"].mean()) / (pbv_std + 1e-6)
        if roe_std < 1e-6:
            roe_z = pd.Series(0.0, index=fundamentals.index)
        else:
            roe_z = (fundamentals["roe"] - fundamentals["roe"].mean()) / (roe_std + 1e-6)

        composite = self._pbv_weight * pbv_z + self._roe_weight * roe_z

        n_select = max(1, int(np.ceil(len(composite) * self._top_quantile)))
        top_stocks = composite.nlargest(n_select)
        weight = 1.0 / n_select

        signals: list[StrategySignal] = []
        for symbol in top_stocks.index:
            rank_pct = float(composite.rank(ascending=True)[symbol] / len(composite))
            signals.append(
                StrategySignal(
                    symbol=symbol,
                    direction=SignalDirection.LONG,
                    target_weight=weight,
                    confidence=round(rank_pct, 4),
                    strategy_id=self._strategy_id,
                    generated_at=as_of_date,
                    metadata={
                        "composite_score": round(float(composite[symbol]), 4),
                        "pbv": round(float(fundamentals.loc[symbol, "pbv"]), 4),
                        "roe": round(float(fundamentals.loc[symbol, "roe"]), 4),
                    },
                )
            )

        logger.info("value_signal_generation_complete", signal_count=len(signals))
        return signals
