"""12-1 month cross-section momentum strategy for IDX equities.

Ranks stocks by trailing 12-month returns (skipping the most recent month to
avoid short-term reversal), then goes long the top quintile with equal weight.

References:
    Jegadeesh & Titman (1993) — *Returns to Buying Winners and Selling Losers*.

Usage::

    strategy = IDXMomentumCrossSectionStrategy()
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

if TYPE_CHECKING:
    from datetime import datetime

logger = get_logger(__name__)

# ── Default universe (LQ45 subset) ──────────────────────────────────────────

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
    "MNCN",
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
    "ISAT",
    "TOWR",
    "TBIG",
    "MDKA",
    "EMTK",
    "ESSA",
    "ACES",
    "ERAA",
    "MAPI",
]


class IDXMomentumCrossSectionStrategy(BaseStrategyInterface):
    """12-1 month cross-section momentum strategy for IDX equities.

    The strategy computes trailing 12-month returns for each stock, subtracts
    the most recent 1-month return (to avoid the short-term reversal anomaly),
    ranks the universe, and goes long the top quintile with equal weight.

    Args:
        universe: List of IDX ticker symbols.
        formation_months: Total look-back window in months (default 12).
        skip_months: Recent months to skip (default 1).
        top_quantile: Fraction of universe to go long (default 0.2 = top quintile).
        strategy_id: Unique identifier for this strategy instance.
    """

    def __init__(
        self,
        universe: list[str] | None = None,
        formation_months: int = 12,
        skip_months: int = 1,
        top_quantile: float = 0.20,
        strategy_id: str = "idx_momentum_12_1",
    ) -> None:
        self._universe = universe or list(_DEFAULT_UNIVERSE)
        self._formation_months = formation_months
        self._skip_months = skip_months
        self._top_quantile = top_quantile
        self._strategy_id = strategy_id

        # Internal state
        self._bar_buffer: dict[str, list[BarData]] = {s: [] for s in self._universe}

        logger.info(
            "momentum_strategy_initialised",
            strategy_id=self._strategy_id,
            universe_size=len(self._universe),
            formation_months=self._formation_months,
            skip_months=self._skip_months,
            top_quantile=self._top_quantile,
        )

    # ── Interface implementation ─────────────────────────────────────────

    def get_parameters(self) -> StrategyParameters:
        """Return current strategy parameters.

        Returns:
            StrategyParameters with momentum-specific configuration.
        """
        return StrategyParameters(
            name="IDX 12-1 Cross-Section Momentum",
            version="1.0.0",
            universe=list(self._universe),
            lookback_days=self._formation_months * 21,  # ~21 trading days per month
            rebalance_frequency="monthly",
            custom={
                "formation_months": self._formation_months,
                "skip_months": self._skip_months,
                "top_quantile": self._top_quantile,
            },
        )

    async def generate_signals(
        self,
        market_data: pd.DataFrame,
        as_of_date: datetime,
    ) -> list[StrategySignal]:
        """Generate momentum signals by ranking 12-1 month returns.

        Args:
            market_data: DataFrame with multi-index ``(date, symbol)`` containing
                at least a ``close`` column.  Dates must cover the full look-back
                window.
            as_of_date: Evaluation date — no data after this date is used.

        Returns:
            List of ``StrategySignal`` for the top-quintile stocks.
        """
        logger.info("momentum_signal_generation_start", as_of_date=as_of_date.isoformat())

        try:
            signals = self._compute_momentum_signals(market_data, as_of_date)
            logger.info(
                "momentum_signal_generation_complete",
                as_of_date=as_of_date.isoformat(),
                signal_count=len(signals),
            )
            return signals
        except (KeyError, ValueError) as exc:
            logger.error("momentum_signal_generation_failed", error=str(exc))
            return []

    async def on_bar(self, bar: BarData) -> list[StrategySignal]:
        """Buffer incoming bars for internal state tracking.

        Momentum strategies rebalance monthly via ``generate_signals``, so
        ``on_bar`` simply stores the bar and returns no signals.

        Args:
            bar: A single OHLCV bar.

        Returns:
            Empty list (momentum signals are generated at rebalance time).
        """
        if bar.symbol in self._bar_buffer:
            self._bar_buffer[bar.symbol].append(bar)
        return []

    async def on_tick(self, tick: TickData) -> list[StrategySignal]:
        """No-op for a monthly-rebalance momentum strategy.

        Args:
            tick: A single tick event.

        Returns:
            Empty list — momentum strategies do not react to ticks.
        """
        return []

    # ── Private helpers ──────────────────────────────────────────────────

    def _compute_momentum_signals(
        self,
        market_data: pd.DataFrame,
        as_of_date: datetime,
    ) -> list[StrategySignal]:
        """Core momentum calculation.

        Steps:
            1. Pivot close prices into a (date x symbol) matrix.
            2. Compute trailing 12-month return for each stock.
            3. Compute trailing 1-month return for each stock.
            4. Momentum score = 12-month return - 1-month return.
            5. Rank stocks and select top quintile.
            6. Assign equal weight to selected stocks.

        Args:
            market_data: Multi-index (date, symbol) DataFrame with ``close``.
            as_of_date: Evaluation date.

        Returns:
            List of StrategySignal for the top-quintile stocks.
        """
        # Pivot to date x symbol close matrix
        if isinstance(market_data.index, pd.MultiIndex):
            close_prices = market_data["close"].unstack(level="symbol")
        else:
            close_prices = market_data.pivot(columns="symbol", values="close")

        # Filter to dates up to as_of_date
        close_prices = close_prices.loc[close_prices.index <= as_of_date]
        close_prices = close_prices.sort_index()

        # Trading days per month approximation
        td_per_month = 21

        formation_days = self._formation_months * td_per_month
        skip_days = self._skip_months * td_per_month

        if len(close_prices) < formation_days:
            logger.warning(
                "momentum_insufficient_data",
                required=formation_days,
                available=len(close_prices),
            )
            return []

        # Trailing 12-month return (from T-252 to T)
        price_now = close_prices.iloc[-1]
        price_12m_ago = close_prices.iloc[-formation_days]
        ret_12m = (price_now / price_12m_ago) - 1.0

        # Trailing 1-month return (from T-21 to T) — the skip period
        price_1m_ago = close_prices.iloc[-skip_days]
        ret_1m = (price_now / price_1m_ago) - 1.0

        # 12-1 momentum score
        momentum_score: pd.Series = ret_12m - ret_1m
        momentum_score = momentum_score.dropna()

        # Filter to universe
        momentum_score = momentum_score.reindex(self._universe).dropna()

        if momentum_score.empty:
            logger.warning("momentum_no_valid_scores")
            return []

        # Rank and select top quintile
        n_select = max(1, int(np.ceil(len(momentum_score) * self._top_quantile)))
        top_stocks = momentum_score.nlargest(n_select)

        # Equal weight
        weight = 1.0 / n_select

        signals: list[StrategySignal] = []
        for symbol in top_stocks.index:
            score = float(momentum_score[symbol])
            # Normalise confidence to [0, 1] using rank percentile
            rank_pct = float((momentum_score.rank(ascending=True)[symbol]) / len(momentum_score))
            signals.append(
                StrategySignal(
                    symbol=symbol,
                    direction=SignalDirection.LONG,
                    target_weight=weight,
                    confidence=round(rank_pct, 4),
                    strategy_id=self._strategy_id,
                    generated_at=as_of_date,
                    metadata={
                        "momentum_score": round(score, 6),
                        "ret_12m": round(float(ret_12m.get(symbol, 0.0)), 6),
                        "ret_1m": round(float(ret_1m.get(symbol, 0.0)), 6),
                    },
                )
            )

        return signals
