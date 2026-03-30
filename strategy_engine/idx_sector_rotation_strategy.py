"""Relative strength sector rotation strategy for IDX equities.

Ranks IDX sector indices by trailing relative strength, rotates into the
top-performing sectors, and selects the most liquid constituents within
each chosen sector.

References:
    Stangl, Jacobsen & Visaltanachoti (2009) — *Sector Rotation over
    Business Cycles*.

Usage::

    strategy = IDXSectorRotationStrategy()
    signals = await strategy.generate_signals(market_data, as_of_date)
"""

from __future__ import annotations

from typing import TYPE_CHECKING

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

# IDX sector mapping
_SECTOR_CONSTITUENTS: dict[str, list[str]] = {
    "FINANCE": ["BBCA", "BBRI", "BMRI", "BBNI", "BRIS"],
    "CONSUMER": ["UNVR", "ICBP", "INDF", "KLBF", "HMSP"],
    "ENERGY": ["ADRO", "PTBA", "ITMG", "MEDC", "PGAS"],
    "BASIC_MATERIALS": ["INCO", "ANTM", "TINS", "SMGR", "INTP"],
    "INFRASTRUCTURE": ["TLKM", "TOWR", "TBIG", "JSMR", "EXCL"],
    "INDUSTRIAL": ["ASII", "UNTR", "CPIN", "SRTG", "INKP"],
    "PROPERTY": ["BSDE", "SMRA", "CTRA", "PWON", "DILD"],
}


class IDXSectorRotationStrategy(BaseStrategyInterface):
    """Relative strength sector rotation strategy.

    Steps:
        1. Compute trailing ``lookback_months`` return for each sector
           (equal-weight of constituents).
        2. Rank sectors by relative strength (return vs IHSG).
        3. Select top ``n_sectors`` sectors.
        4. Within each sector, select top ``stocks_per_sector`` by momentum.
        5. Assign equal weight across all selected stocks.

    Args:
        sector_map: Mapping of sector name to constituent tickers.
        lookback_months: Months for relative strength calculation.
        n_sectors: Number of top sectors to rotate into.
        stocks_per_sector: Number of stocks per selected sector.
        strategy_id: Unique strategy identifier.
    """

    def __init__(
        self,
        sector_map: dict[str, list[str]] | None = None,
        lookback_months: int = 3,
        n_sectors: int = 3,
        stocks_per_sector: int = 3,
        strategy_id: str = "idx_sector_rotation",
        instrument_metadata: pd.DataFrame | None = None,
    ) -> None:
        self._sectors = sector_map or dict(_SECTOR_CONSTITUENTS)
        self._lookback_months = lookback_months
        self._n_sectors = n_sectors
        self._stocks_per_sector = stocks_per_sector
        self._strategy_id = strategy_id
        self._instrument_metadata = instrument_metadata

        self._all_symbols = [s for syms in self._sectors.values() for s in syms]

        logger.info(
            "sector_rotation_initialised",
            strategy_id=self._strategy_id,
            num_sectors=len(self._sectors),
            lookback_months=self._lookback_months,
        )

    def get_parameters(self) -> StrategyParameters:
        return StrategyParameters(
            name="IDX Relative Strength Sector Rotation",
            version="1.0.0",
            universe=list(self._all_symbols),
            lookback_days=self._lookback_months * 21,
            rebalance_frequency="monthly",
            custom={
                "n_sectors": self._n_sectors,
                "stocks_per_sector": self._stocks_per_sector,
                "lookback_months": self._lookback_months,
            },
        )

    async def generate_signals(self, market_data: pd.DataFrame, as_of_date: datetime) -> list[StrategySignal]:
        logger.info("sector_rotation_signal_start", as_of_date=as_of_date.isoformat())
        try:
            return self._compute_rotation_signals(market_data, as_of_date)
        except (KeyError, ValueError) as exc:
            logger.error("sector_rotation_signal_failed", error=str(exc))
            return []

    async def on_bar(self, bar: BarData) -> list[StrategySignal]:
        return []

    async def on_tick(self, tick: TickData) -> list[StrategySignal]:
        return []

    def _compute_rotation_signals(self, market_data: pd.DataFrame, as_of_date: datetime) -> list[StrategySignal]:
        if isinstance(market_data.index, pd.MultiIndex):
            close = market_data["close"].unstack(level="symbol")
        else:
            close = market_data.pivot(columns="symbol", values="close")

        close = close.loc[close.index <= as_of_date].sort_index()
        lookback_days = self._lookback_months * 21

        if len(close) < lookback_days:
            logger.warning("sector_rotation_insufficient_data")
            return []

        window = close.iloc[-lookback_days:]

        # Survivorship bias filter (M-1)
        tradable = set(filter_tradable_symbols(self._all_symbols, as_of_date, self._instrument_metadata))

        # Compute sector returns (equal-weight of constituents).
        sector_returns: dict[str, float] = {}
        for sector, constituents in self._sectors.items():
            available = [c for c in constituents if c in window.columns and c in tradable]
            if not available:
                continue
            sector_ret = window[available].pct_change().mean(axis=1).add(1).prod() - 1
            sector_returns[sector] = float(sector_ret)

        if not sector_returns:
            return []

        ranked = sorted(sector_returns.items(), key=lambda x: x[1], reverse=True)
        top_sectors = ranked[: self._n_sectors]

        # Within each top sector, pick best-performing stocks.
        selected: list[tuple[str, float, str]] = []
        for sector, sector_ret in top_sectors:
            constituents = [c for c in self._sectors[sector] if c in window.columns and c in tradable]
            stock_returns: dict[str, float] = {}
            for sym in constituents:
                sym_close = window[sym].dropna()
                if len(sym_close) >= 2:
                    stock_returns[sym] = float(sym_close.iloc[-1] / sym_close.iloc[0] - 1)

            sorted_stocks = sorted(stock_returns.items(), key=lambda x: x[1], reverse=True)
            for sym, ret in sorted_stocks[: self._stocks_per_sector]:
                selected.append((sym, ret, sector))

        if not selected:
            return []

        weight = 1.0 / len(selected)
        signals: list[StrategySignal] = []
        for sym, ret, sector in selected:
            signals.append(
                StrategySignal(
                    symbol=sym,
                    direction=SignalDirection.LONG,
                    target_weight=weight,
                    confidence=round(min(max(ret + 0.5, 0.0), 1.0), 4),
                    strategy_id=self._strategy_id,
                    generated_at=as_of_date,
                    metadata={
                        "sector": sector,
                        "stock_return": round(ret, 6),
                        "sector_return": round(sector_returns.get(sector, 0.0), 6),
                    },
                )
            )

        logger.info("sector_rotation_signal_complete", signal_count=len(signals))
        return signals
