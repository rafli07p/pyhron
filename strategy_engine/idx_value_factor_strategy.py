"""PBV + ROE value factor strategy with quarterly rebalance.

Screens for stocks with low Price-to-Book Value (PBV) and high Return on
Equity (ROE), assigns equal weight, and rebalances quarterly.

Usage::

    strategy = IDXValueFactorStrategy()
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

_DEFAULT_UNIVERSE: list[str] = [
    "BBCA", "BBRI", "BMRI", "BBNI", "TLKM", "ASII", "UNVR", "HMSP",
    "GGRM", "KLBF", "ICBP", "INDF", "SMGR", "PTBA", "ADRO", "ITMG",
    "UNTR", "PGAS", "JSMR", "CPIN", "INKP", "INTP", "EXCL", "TOWR",
    "TBIG", "MDKA", "EMTK", "ESSA", "ACES", "ERAA", "MAPI", "MNCN",
    "BSDE", "SMRA", "WIKA", "WSKT", "ANTM", "TINS", "INCO", "ISAT",
]


class IDXValueFactorStrategy(BaseStrategyInterface):
    """PBV + ROE value factor strategy with quarterly rebalance.

    The strategy scores each stock using a composite value-quality metric:

        ``composite_score = (1 - pbv_rank_pct) * pbv_weight + roe_rank_pct * roe_weight``

    Where rank percentiles are computed cross-sectionally.  Stocks in the
    top quintile by composite score are selected and equally weighted.

    Args:
        universe: List of IDX ticker symbols.
        pbv_weight: Weight for the PBV factor in the composite (default 0.5).
        roe_weight: Weight for the ROE factor in the composite (default 0.5).
        max_pbv: Maximum PBV to include in the screen (default 3.0).
        min_roe: Minimum ROE to include in the screen (default 0.05 = 5%).
        top_quantile: Fraction of stocks to select (default 0.2).
        rebalance_months: Months in which to rebalance (default Q1 ends:
            March, June, September, December).
        strategy_id: Unique identifier for this strategy instance.
    """

    def __init__(
        self,
        universe: list[str] | None = None,
        pbv_weight: float = 0.5,
        roe_weight: float = 0.5,
        max_pbv: float = 3.0,
        min_roe: float = 0.05,
        top_quantile: float = 0.20,
        rebalance_months: list[int] | None = None,
        strategy_id: str = "idx_value_factor",
    ) -> None:
        self._universe = universe or list(_DEFAULT_UNIVERSE)
        self._pbv_weight = pbv_weight
        self._roe_weight = roe_weight
        self._max_pbv = max_pbv
        self._min_roe = min_roe
        self._top_quantile = top_quantile
        self._rebalance_months = rebalance_months or [3, 6, 9, 12]
        self._strategy_id = strategy_id

        # Current portfolio holdings from last rebalance
        self._current_holdings: dict[str, float] = {}
        self._last_rebalance_month: int | None = None

        logger.info(
            "value_factor_strategy_initialised",
            strategy_id=self._strategy_id,
            universe_size=len(self._universe),
            pbv_weight=self._pbv_weight,
            roe_weight=self._roe_weight,
            max_pbv=self._max_pbv,
            min_roe=self._min_roe,
        )

    # ── Interface implementation ─────────────────────────────────────────

    def get_parameters(self) -> StrategyParameters:
        """Return current strategy parameters.

        Returns:
            StrategyParameters with value-factor-specific configuration.
        """
        return StrategyParameters(
            name="IDX PBV + ROE Value Factor",
            version="1.0.0",
            universe=list(self._universe),
            lookback_days=90,
            rebalance_frequency="quarterly",
            custom={
                "pbv_weight": self._pbv_weight,
                "roe_weight": self._roe_weight,
                "max_pbv": self._max_pbv,
                "min_roe": self._min_roe,
                "top_quantile": self._top_quantile,
                "rebalance_months": self._rebalance_months,
            },
        )

    async def generate_signals(
        self,
        market_data: pd.DataFrame,
        as_of_date: datetime,
    ) -> list[StrategySignal]:
        """Generate value-factor rebalance signals.

        The ``market_data`` DataFrame must include ``pbv`` and ``roe`` columns
        in addition to ``close``.  If the current month is not a rebalance
        month, the method returns the existing holdings as REBALANCE signals
        (i.e., hold current portfolio).

        Args:
            market_data: DataFrame with multi-index ``(date, symbol)`` and
                columns ``close``, ``pbv``, ``roe``.
            as_of_date: Evaluation date.

        Returns:
            List of LONG/REBALANCE signals for the value-screened portfolio.
        """
        logger.info("value_factor_signal_generation_start", as_of_date=as_of_date.isoformat())

        current_month = as_of_date.month

        # Check if this is a rebalance month
        if (
            current_month not in self._rebalance_months
            and self._last_rebalance_month is not None
        ):
            logger.info(
                "value_factor_not_rebalance_month",
                month=current_month,
                holding_count=len(self._current_holdings),
            )
            return self._emit_hold_signals(as_of_date)

        try:
            signals = self._compute_value_signals(market_data, as_of_date)
            self._last_rebalance_month = current_month
            logger.info(
                "value_factor_signal_generation_complete",
                as_of_date=as_of_date.isoformat(),
                signal_count=len(signals),
            )
            return signals
        except (KeyError, ValueError) as exc:
            logger.error("value_factor_signal_generation_failed", error=str(exc))
            return []

    async def on_bar(self, bar: BarData) -> list[StrategySignal]:
        """No-op for quarterly rebalance strategy.

        Args:
            bar: A single OHLCV bar.

        Returns:
            Empty list.
        """
        return []

    async def on_tick(self, tick: TickData) -> list[StrategySignal]:
        """No-op for quarterly rebalance strategy.

        Args:
            tick: A single tick event.

        Returns:
            Empty list.
        """
        return []

    # ── Private helpers ──────────────────────────────────────────────────

    def _compute_value_signals(
        self,
        market_data: pd.DataFrame,
        as_of_date: datetime,
    ) -> list[StrategySignal]:
        """Core value-factor screening and signal generation.

        Steps:
            1. Extract latest PBV and ROE for each stock.
            2. Apply hard filters (max PBV, min ROE).
            3. Rank stocks by composite score.
            4. Select top quintile.
            5. Close positions no longer in the portfolio.
            6. Open/maintain positions in selected stocks.

        Args:
            market_data: Multi-index (date, symbol) DataFrame with
                ``close``, ``pbv``, ``roe``.
            as_of_date: Evaluation date.

        Returns:
            List of trading signals.
        """
        # Extract the latest fundamental data per symbol
        if isinstance(market_data.index, pd.MultiIndex):
            latest = market_data.loc[market_data.index.get_level_values("date") <= as_of_date]
            latest = latest.groupby(level="symbol").last()
        else:
            latest = market_data.loc[market_data.index <= as_of_date].copy()

        # Ensure required columns exist
        required_cols = {"pbv", "roe"}
        available_cols = set(latest.columns)
        if not required_cols.issubset(available_cols):
            logger.warning(
                "value_factor_missing_columns",
                required=list(required_cols),
                available=list(available_cols),
            )
            # Fall back to close-based proxy if fundamentals are missing
            return self._fallback_price_based_signals(market_data, as_of_date)

        # Filter to universe
        universe_data = latest.loc[latest.index.isin(self._universe)].copy()

        if universe_data.empty:
            logger.warning("value_factor_no_universe_data")
            return []

        # Hard filters
        screened = universe_data[
            (universe_data["pbv"] > 0)
            & (universe_data["pbv"] <= self._max_pbv)
            & (universe_data["roe"] >= self._min_roe)
        ].copy()

        if screened.empty:
            logger.warning("value_factor_screen_empty_after_filters")
            return []

        # Cross-sectional rank percentiles
        screened["pbv_rank_pct"] = screened["pbv"].rank(ascending=True, pct=True)
        screened["roe_rank_pct"] = screened["roe"].rank(ascending=True, pct=True)

        # Composite score: low PBV (inverted rank) + high ROE
        screened["composite_score"] = (
            (1.0 - screened["pbv_rank_pct"]) * self._pbv_weight
            + screened["roe_rank_pct"] * self._roe_weight
        )

        # Select top quintile
        n_select = max(1, int(np.ceil(len(screened) * self._top_quantile)))
        selected = screened.nlargest(n_select, "composite_score")

        weight = 1.0 / n_select

        signals: list[StrategySignal] = []

        # Close signals for stocks no longer in the portfolio
        new_holdings = set(selected.index)
        for symbol in list(self._current_holdings.keys()):
            if symbol not in new_holdings:
                signals.append(
                    StrategySignal(
                        symbol=symbol,
                        direction=SignalDirection.CLOSE,
                        target_weight=0.0,
                        confidence=0.9,
                        strategy_id=self._strategy_id,
                        generated_at=as_of_date,
                        metadata={"exit_reason": "quarterly_rebalance_drop"},
                    )
                )

        # Long signals for selected stocks
        self._current_holdings = {}
        for symbol in selected.index:
            row = selected.loc[symbol]
            composite = float(row["composite_score"])
            confidence = min(0.95, composite)

            self._current_holdings[symbol] = weight

            signals.append(
                StrategySignal(
                    symbol=symbol,
                    direction=SignalDirection.LONG,
                    target_weight=weight,
                    confidence=round(confidence, 4),
                    strategy_id=self._strategy_id,
                    generated_at=as_of_date,
                    metadata={
                        "pbv": round(float(row["pbv"]), 4),
                        "roe": round(float(row["roe"]), 4),
                        "composite_score": round(composite, 4),
                        "pbv_rank_pct": round(float(row["pbv_rank_pct"]), 4),
                        "roe_rank_pct": round(float(row["roe_rank_pct"]), 4),
                    },
                )
            )

        return signals

    def _fallback_price_based_signals(
        self,
        market_data: pd.DataFrame,
        as_of_date: datetime,
    ) -> list[StrategySignal]:
        """Fallback when fundamental data is unavailable.

        Uses trailing return as a crude quality proxy. This should rarely
        be invoked in production.

        Args:
            market_data: Market data DataFrame.
            as_of_date: Evaluation date.

        Returns:
            Empty signal list with a warning logged.
        """
        logger.warning(
            "value_factor_using_fallback",
            reason="fundamental_data_missing",
            as_of_date=as_of_date.isoformat(),
        )
        return []

    def _emit_hold_signals(self, as_of_date: datetime) -> list[StrategySignal]:
        """Re-emit current holdings as REBALANCE signals (hold portfolio).

        Args:
            as_of_date: Signal timestamp.

        Returns:
            REBALANCE signals for all current holdings.
        """
        signals: list[StrategySignal] = []
        for symbol, weight in self._current_holdings.items():
            signals.append(
                StrategySignal(
                    symbol=symbol,
                    direction=SignalDirection.REBALANCE,
                    target_weight=weight,
                    confidence=0.8,
                    strategy_id=self._strategy_id,
                    generated_at=as_of_date,
                    metadata={"hold_reason": "not_rebalance_month"},
                )
            )
        return signals
