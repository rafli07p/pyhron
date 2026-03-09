"""Relative-strength sector rotation strategy for IDX.

Compares 1-month returns across IDX sectors, overweights the top 3 sectors,
and allocates equally within each selected sector using representative
liquid stocks.

Usage::

    strategy = IDXSectorRotationStrategy()
    signals = await strategy.generate_signals(market_data, as_of_date)
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

import numpy as np
import pandas as pd

from shared.structured_json_logger import get_logger
from strategy_engine.base_strategy_interface import (
    BaseStrategyInterface,
    BarData,
    SignalDirection,
    StrategyParameters,
    StrategySignal,
    TickData,
)

logger = get_logger(__name__)

# ── IDX Sector Definitions ──────────────────────────────────────────────────
# Maps each sector to its representative liquid stocks and sector index symbol.

IDX_SECTORS: dict[str, dict[str, Any]] = {
    "FINANCIALS": {
        "index": "IDXFINANCE",
        "stocks": ["BBCA", "BBRI", "BMRI", "BBNI"],
    },
    "CONSUMER_STAPLES": {
        "index": "IDXNONCYC",
        "stocks": ["UNVR", "ICBP", "INDF", "KLBF"],
    },
    "CONSUMER_DISCRETIONARY": {
        "index": "IDXCYCLIC",
        "stocks": ["ASII", "ACES", "ERAA", "MAPI"],
    },
    "ENERGY": {
        "index": "IDXENERGY",
        "stocks": ["ADRO", "ITMG", "PTBA", "PGAS"],
    },
    "MATERIALS": {
        "index": "IDXBASIC",
        "stocks": ["INKP", "SMGR", "INTP", "TINS"],
    },
    "TELECOM": {
        "index": "IDXINFRA",
        "stocks": ["TLKM", "EXCL", "ISAT", "TOWR"],
    },
    "PROPERTY": {
        "index": "IDXPROPERT",
        "stocks": ["BSDE", "SMRA", "CTRA", "PWON"],
    },
    "MINING": {
        "index": "IDXMINING",
        "stocks": ["ANTM", "INCO", "MDKA", "ESSA"],
    },
    "INDUSTRIALS": {
        "index": "IDXINDUST",
        "stocks": ["UNTR", "WIKA", "WSKT", "JSMR"],
    },
    "TOBACCO": {
        "index": "IDXTOBACCO",
        "stocks": ["HMSP", "GGRM"],
    },
}


class IDXSectorRotationStrategy(BaseStrategyInterface):
    """Relative-strength sector rotation strategy for IDX.

    The strategy computes the trailing 1-month return for each IDX sector,
    ranks sectors by momentum, selects the top ``n_top_sectors`` sectors,
    and allocates equally across representative stocks within each selected
    sector.

    Args:
        sectors: Sector definition mapping.  Defaults to ``IDX_SECTORS``.
        n_top_sectors: Number of top sectors to overweight (default 3).
        momentum_period: Look-back period in trading days for sector
            momentum calculation (default 21 = ~1 month).
        use_sector_index: If True, compute sector returns from sector
            index symbols; otherwise average constituent returns.
        strategy_id: Unique identifier for this strategy instance.
    """

    def __init__(
        self,
        sectors: dict[str, dict[str, Any]] | None = None,
        n_top_sectors: int = 3,
        momentum_period: int = 21,
        use_sector_index: bool = False,
        strategy_id: str = "idx_sector_rotation",
    ) -> None:
        self._sectors = sectors or dict(IDX_SECTORS)
        self._n_top_sectors = n_top_sectors
        self._momentum_period = momentum_period
        self._use_sector_index = use_sector_index
        self._strategy_id = strategy_id

        # Build full universe
        self._universe: list[str] = []
        for sector_info in self._sectors.values():
            self._universe.extend(sector_info["stocks"])
            if self._use_sector_index:
                self._universe.append(sector_info["index"])
        self._universe = sorted(set(self._universe))

        # Current sector allocation
        self._selected_sectors: list[str] = []

        logger.info(
            "sector_rotation_strategy_initialised",
            strategy_id=self._strategy_id,
            sector_count=len(self._sectors),
            n_top_sectors=self._n_top_sectors,
            momentum_period=self._momentum_period,
        )

    # ── Interface implementation ─────────────────────────────────────────

    def get_parameters(self) -> StrategyParameters:
        """Return current strategy parameters.

        Returns:
            StrategyParameters with sector-rotation-specific configuration.
        """
        return StrategyParameters(
            name="IDX Sector Rotation (Relative Strength)",
            version="1.0.0",
            universe=list(self._universe),
            lookback_days=self._momentum_period + 10,
            rebalance_frequency="monthly",
            custom={
                "n_top_sectors": self._n_top_sectors,
                "momentum_period": self._momentum_period,
                "sectors": list(self._sectors.keys()),
                "use_sector_index": self._use_sector_index,
            },
        )

    async def generate_signals(
        self,
        market_data: pd.DataFrame,
        as_of_date: datetime,
    ) -> list[StrategySignal]:
        """Generate sector-rotation signals based on relative strength.

        Args:
            market_data: DataFrame with multi-index ``(date, symbol)`` and
                column ``close``.
            as_of_date: Evaluation date.

        Returns:
            List of LONG/CLOSE signals reflecting the sector rotation.
        """
        logger.info("sector_rotation_signal_generation_start", as_of_date=as_of_date.isoformat())

        try:
            signals = self._compute_sector_signals(market_data, as_of_date)
            logger.info(
                "sector_rotation_signal_generation_complete",
                as_of_date=as_of_date.isoformat(),
                signal_count=len(signals),
            )
            return signals
        except (KeyError, ValueError) as exc:
            logger.error("sector_rotation_signal_generation_failed", error=str(exc))
            return []

    async def on_bar(self, bar: BarData) -> list[StrategySignal]:
        """No-op for monthly sector rotation.

        Args:
            bar: A single OHLCV bar.

        Returns:
            Empty list.
        """
        return []

    async def on_tick(self, tick: TickData) -> list[StrategySignal]:
        """No-op for monthly sector rotation.

        Args:
            tick: A single tick event.

        Returns:
            Empty list.
        """
        return []

    # ── Private helpers ──────────────────────────────────────────────────

    def _compute_sector_returns(
        self,
        close_prices: pd.DataFrame,
    ) -> dict[str, float]:
        """Compute trailing 1-month return for each sector.

        If ``use_sector_index`` is True, uses the sector index symbol's
        return.  Otherwise, averages the returns of constituent stocks.

        Args:
            close_prices: Date x symbol close-price matrix.

        Returns:
            Mapping of sector name to 1-month return.
        """
        sector_returns: dict[str, float] = {}

        for sector_name, sector_info in self._sectors.items():
            if self._use_sector_index:
                idx_sym = sector_info["index"]
                if idx_sym in close_prices.columns:
                    series = close_prices[idx_sym].dropna()
                    if len(series) >= self._momentum_period + 1:
                        ret = float(
                            series.iloc[-1] / series.iloc[-self._momentum_period - 1] - 1.0
                        )
                        sector_returns[sector_name] = ret
                        continue

            # Average constituent returns
            stocks = sector_info["stocks"]
            available = [s for s in stocks if s in close_prices.columns]
            if not available:
                continue

            stock_returns: list[float] = []
            for stock in available:
                series = close_prices[stock].dropna()
                if len(series) >= self._momentum_period + 1:
                    ret = float(
                        series.iloc[-1] / series.iloc[-self._momentum_period - 1] - 1.0
                    )
                    stock_returns.append(ret)

            if stock_returns:
                sector_returns[sector_name] = float(np.mean(stock_returns))

        return sector_returns

    def _compute_sector_signals(
        self,
        market_data: pd.DataFrame,
        as_of_date: datetime,
    ) -> list[StrategySignal]:
        """Core sector rotation signal computation.

        Steps:
            1. Pivot to date x symbol close matrix.
            2. Compute 1-month returns per sector.
            3. Rank sectors and select top N.
            4. Allocate equal weight across stocks in selected sectors.
            5. Generate CLOSE signals for stocks in de-selected sectors.

        Args:
            market_data: Multi-index (date, symbol) DataFrame with ``close``.
            as_of_date: Evaluation date.

        Returns:
            List of trading signals.
        """
        # Pivot
        if isinstance(market_data.index, pd.MultiIndex):
            close_prices = market_data["close"].unstack(level="symbol")
        else:
            close_prices = market_data.pivot(columns="symbol", values="close")

        close_prices = close_prices.loc[close_prices.index <= as_of_date].sort_index()

        if len(close_prices) < self._momentum_period + 1:
            logger.warning(
                "sector_rotation_insufficient_data",
                required=self._momentum_period + 1,
                available=len(close_prices),
            )
            return []

        # Compute sector returns
        sector_returns = self._compute_sector_returns(close_prices)

        if len(sector_returns) < self._n_top_sectors:
            logger.warning(
                "sector_rotation_insufficient_sectors",
                available=len(sector_returns),
                required=self._n_top_sectors,
            )
            return []

        # Rank and select top N sectors
        sorted_sectors = sorted(sector_returns.items(), key=lambda x: x[1], reverse=True)
        top_sectors = [name for name, _ in sorted_sectors[: self._n_top_sectors]]
        previous_sectors = list(self._selected_sectors)
        self._selected_sectors = top_sectors

        logger.info(
            "sector_rotation_selected",
            top_sectors=top_sectors,
            sector_returns={k: round(v, 4) for k, v in sorted_sectors},
        )

        # Collect stocks in selected sectors
        selected_stocks: list[str] = []
        stock_to_sector: dict[str, str] = {}
        for sector_name in top_sectors:
            stocks = self._sectors[sector_name]["stocks"]
            for stock in stocks:
                if stock in close_prices.columns:
                    selected_stocks.append(stock)
                    stock_to_sector[stock] = sector_name

        if not selected_stocks:
            logger.warning("sector_rotation_no_stocks_in_selected_sectors")
            return []

        # Equal weight across all selected stocks
        weight = 1.0 / len(selected_stocks)

        signals: list[StrategySignal] = []

        # CLOSE signals for stocks in previously-selected but now de-selected sectors
        deselected_sectors = set(previous_sectors) - set(top_sectors)
        for sector_name in deselected_sectors:
            for stock in self._sectors[sector_name]["stocks"]:
                signals.append(
                    StrategySignal(
                        symbol=stock,
                        direction=SignalDirection.CLOSE,
                        target_weight=0.0,
                        confidence=0.85,
                        strategy_id=self._strategy_id,
                        generated_at=as_of_date,
                        metadata={
                            "exit_reason": "sector_deselected",
                            "sector": sector_name,
                            "sector_return": round(sector_returns.get(sector_name, 0.0), 4),
                        },
                    )
                )

        # LONG signals for stocks in selected sectors
        for stock in selected_stocks:
            sector_name = stock_to_sector[stock]
            sector_ret = sector_returns.get(sector_name, 0.0)

            # Confidence based on sector rank
            rank_idx = top_sectors.index(sector_name)
            confidence = 0.9 - rank_idx * 0.1  # top sector gets 0.9, second 0.8, etc.

            signals.append(
                StrategySignal(
                    symbol=stock,
                    direction=SignalDirection.LONG,
                    target_weight=weight,
                    confidence=round(max(0.5, confidence), 4),
                    strategy_id=self._strategy_id,
                    generated_at=as_of_date,
                    metadata={
                        "sector": sector_name,
                        "sector_1m_return": round(sector_ret, 4),
                        "sector_rank": rank_idx + 1,
                    },
                )
            )

        return signals
