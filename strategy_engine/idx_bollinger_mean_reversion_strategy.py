"""Bollinger Band mean-reversion strategy with IHSG regime filter.

Enters long when price touches the lower Bollinger Band (-2 sigma), exits at
the middle band (20-day SMA).  A regime filter skips all entries when the
IHSG (Jakarta Composite Index) is below its 200-day moving average — i.e.,
the strategy only trades in bull regimes.

Usage::

    strategy = IDXBollingerMeanReversionStrategy()
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
    "EXCL",
    "TOWR",
]


class IDXBollingerMeanReversionStrategy(BaseStrategyInterface):
    """Bollinger Band +/- 2 sigma mean reversion with IHSG regime filter.

    The strategy monitors each stock's position relative to its Bollinger
    Bands.  Entry is triggered when price touches or crosses below the lower
    band.  The exit target is the middle band (SMA).  All new entries are
    suppressed when the IHSG composite index is below its 200-day simple
    moving average, acting as a bear-market regime filter.

    Args:
        universe: List of IDX ticker symbols to monitor.
        bb_period: Look-back window for Bollinger Bands (default 20).
        bb_std: Number of standard deviations for the bands (default 2.0).
        regime_ma_period: Moving-average period for the IHSG regime filter
            (default 200).
        ihsg_symbol: Symbol for the Jakarta Composite Index (default ``IHSG``).
        equal_weight_per_position: Weight allocated to each open position.
        strategy_id: Unique identifier for this strategy instance.
    """

    def __init__(
        self,
        universe: list[str] | None = None,
        bb_period: int = 20,
        bb_std: float = 2.0,
        regime_ma_period: int = 200,
        ihsg_symbol: str = "IHSG",
        equal_weight_per_position: float = 0.05,
        strategy_id: str = "idx_bollinger_mean_reversion",
        instrument_metadata: pd.DataFrame | None = None,
    ) -> None:
        self._universe = universe or list(_DEFAULT_UNIVERSE)
        self._bb_period = bb_period
        self._bb_std = bb_std
        self._regime_ma_period = regime_ma_period
        self._ihsg_symbol = ihsg_symbol
        self._weight = equal_weight_per_position
        self._strategy_id = strategy_id
        self._instrument_metadata = instrument_metadata

        # Track open positions: symbol -> entry price
        self._open_positions: dict[str, float] = {}

        logger.info(
            "bollinger_strategy_initialised",
            strategy_id=self._strategy_id,
            universe_size=len(self._universe),
            bb_period=self._bb_period,
            bb_std=self._bb_std,
        )

    # Interface implementation

    def get_parameters(self) -> StrategyParameters:
        """Return current strategy parameters.

        Returns:
            StrategyParameters with Bollinger-Band-specific configuration.
        """
        return StrategyParameters(
            name="IDX Bollinger Band Mean Reversion",
            version="1.0.0",
            universe=list(self._universe),
            lookback_days=max(self._bb_period, self._regime_ma_period) + 10,
            rebalance_frequency="daily",
            custom={
                "bb_period": self._bb_period,
                "bb_std": self._bb_std,
                "regime_ma_period": self._regime_ma_period,
                "ihsg_symbol": self._ihsg_symbol,
                "weight_per_position": self._weight,
            },
        )

    async def generate_signals(
        self,
        market_data: pd.DataFrame,
        as_of_date: datetime,
    ) -> list[StrategySignal]:
        """Scan the universe for Bollinger-Band entry and exit signals.

        Args:
            market_data: DataFrame with multi-index ``(date, symbol)`` and
                columns ``close`` (at minimum).  Must include the ``IHSG``
                symbol for the regime filter.
            as_of_date: Evaluation date.

        Returns:
            List of entry (LONG) and exit (CLOSE) signals.
        """
        logger.info("bollinger_signal_generation_start", as_of_date=as_of_date.isoformat())

        try:
            signals = self._compute_bollinger_signals(market_data, as_of_date)
            logger.info(
                "bollinger_signal_generation_complete",
                as_of_date=as_of_date.isoformat(),
                signal_count=len(signals),
            )
            return signals
        except (KeyError, ValueError) as exc:
            logger.error("bollinger_signal_generation_failed", error=str(exc))
            return []

    async def on_bar(self, bar: BarData) -> list[StrategySignal]:
        """Process a single bar and check Bollinger-Band conditions.

        For open positions, check if price has reverted to the middle band
        (exit signal).  For new entries, defer to ``generate_signals``.

        Args:
            bar: A single OHLCV bar.

        Returns:
            Possible CLOSE signals for mean-reverted positions.
        """
        # Exit logic is consolidated in _compute_bollinger_signals() which
        # uses the middle band (SMA) as the canonical exit rule.  The previous
        # 2% profit-target exit here was removed to avoid conflicting with the
        # middle-band exit and to keep a single source of truth for exits.
        return []

    async def on_tick(self, tick: TickData) -> list[StrategySignal]:
        """No-op for a daily-rebalance mean-reversion strategy.

        Args:
            tick: A single tick event.

        Returns:
            Empty list.
        """
        return []

    # Private helpers

    def _check_regime_filter(self, close_prices: pd.DataFrame) -> bool:
        """Check whether the IHSG is above its 200-day MA (bull regime).

        Args:
            close_prices: Date x symbol close-price matrix.

        Returns:
            True if the regime is bullish (IHSG above 200-day MA).
        """
        if self._ihsg_symbol not in close_prices.columns:
            logger.warning("bollinger_regime_filter_missing_ihsg")
            return True  # Default to allowing trades if IHSG data unavailable

        ihsg_series = close_prices[self._ihsg_symbol].dropna()
        if len(ihsg_series) < self._regime_ma_period:
            logger.warning(
                "bollinger_regime_filter_insufficient_data",
                required=self._regime_ma_period,
                available=len(ihsg_series),
            )
            return True

        ma_200 = ihsg_series.rolling(window=self._regime_ma_period).mean().iloc[-1]
        current_price = ihsg_series.iloc[-1]
        is_bullish = current_price > ma_200

        logger.debug(
            "bollinger_regime_check",
            ihsg_price=round(float(current_price), 2),
            ma_200=round(float(ma_200), 2),
            is_bullish=is_bullish,
        )

        return bool(is_bullish)

    def _compute_bollinger_bands(self, series: pd.Series) -> tuple[pd.Series, pd.Series, pd.Series]:
        """Compute Bollinger Bands for a price series.

        Args:
            series: Close-price series.

        Returns:
            Tuple of (middle_band, upper_band, lower_band) as pd.Series.
        """
        middle = series.rolling(window=self._bb_period).mean()
        std = series.rolling(window=self._bb_period).std(ddof=1)
        upper = middle + self._bb_std * std
        lower = middle - self._bb_std * std
        return middle, upper, lower

    def _compute_bollinger_signals(
        self,
        market_data: pd.DataFrame,
        as_of_date: datetime,
    ) -> list[StrategySignal]:
        """Core Bollinger-Band signal computation.

        Steps:
            1. Pivot to date x symbol close matrix.
            2. Apply regime filter (IHSG > 200-day MA).
            3. For each stock, compute Bollinger Bands.
            4. Entry if today's close <= lower band AND regime is bullish.
            5. Exit if today's close >= middle band AND position is open.

        Args:
            market_data: Multi-index (date, symbol) DataFrame with ``close``.
            as_of_date: Evaluation date.

        Returns:
            List of entry and exit signals.
        """
        # Pivot to date x symbol close matrix
        if isinstance(market_data.index, pd.MultiIndex):
            close_prices = market_data["close"].unstack(level="symbol")
        else:
            close_prices = market_data.pivot(columns="symbol", values="close")

        close_prices = close_prices.loc[close_prices.index <= as_of_date].sort_index()

        if len(close_prices) < self._bb_period:
            logger.warning(
                "bollinger_insufficient_data",
                required=self._bb_period,
                available=len(close_prices),
            )
            return []

        # Regime filter
        is_bullish = self._check_regime_filter(close_prices)

        # Survivorship bias filter (M-1)
        universe = filter_tradable_symbols(self._universe, as_of_date, self._instrument_metadata)

        signals: list[StrategySignal] = []

        for symbol in universe:
            if symbol not in close_prices.columns:
                continue

            series = close_prices[symbol].dropna()
            if len(series) < self._bb_period:
                continue

            middle, upper, lower = self._compute_bollinger_bands(series)

            current_close = float(series.iloc[-1])
            current_middle = float(middle.iloc[-1])
            current_lower = float(lower.iloc[-1])
            current_upper = float(upper.iloc[-1])

            # Previous close for cross-detection
            prev_close = float(series.iloc[-2]) if len(series) >= 2 else current_close

            # Exit: price reverted to or above middle band
            if symbol in self._open_positions:
                if current_close >= current_middle:
                    signals.append(
                        StrategySignal(
                            symbol=symbol,
                            direction=SignalDirection.CLOSE,
                            target_weight=0.0,
                            confidence=0.85,
                            strategy_id=self._strategy_id,
                            generated_at=as_of_date,
                            metadata={
                                "exit_reason": "middle_band_touch",
                                "close": current_close,
                                "middle_band": round(current_middle, 2),
                                "entry_price": self._open_positions[symbol],
                            },
                        )
                    )
                    del self._open_positions[symbol]
                continue  # skip entry check for open positions

            # Entry: price touches or crosses below lower band in bullish regime
            if is_bullish and current_close <= current_lower:
                # Compute z-score for confidence
                bb_width = current_upper - current_lower
                if bb_width > 0:
                    distance_below = (current_lower - current_close) / bb_width
                    confidence = min(0.95, 0.5 + distance_below)
                else:
                    confidence = 0.5

                signals.append(
                    StrategySignal(
                        symbol=symbol,
                        direction=SignalDirection.LONG,
                        target_weight=self._weight,
                        confidence=round(confidence, 4),
                        strategy_id=self._strategy_id,
                        generated_at=as_of_date,
                        metadata={
                            "entry_reason": "lower_band_touch",
                            "close": current_close,
                            "lower_band": round(current_lower, 2),
                            "middle_band": round(current_middle, 2),
                            "upper_band": round(current_upper, 2),
                            "prev_close": prev_close,
                        },
                    )
                )
                self._open_positions[symbol] = current_close

        return signals
