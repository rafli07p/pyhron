"""Chart Panel for the Enthropy Terminal.

Renders OHLCV candlestick charts with overlaid technical indicators.
Fetches market data through the terminal's DataClient for live and
historical display.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from typing import Any, Optional

from shared.schemas.market_events import BarEvent

logger = logging.getLogger(__name__)


@dataclass
class IndicatorConfig:
    """Configuration for a technical indicator overlay or study."""

    name: str
    params: dict[str, Any] = field(default_factory=dict)
    visible: bool = True
    color: str | None = None


@dataclass
class ChartState:
    """Internal state of a chart panel."""

    symbol: str = ""
    timeframe: str = "1D"
    bars: list[BarEvent] = field(default_factory=list)
    indicators: list[IndicatorConfig] = field(default_factory=list)
    last_update: datetime | None = None


class ChartPanel:
    """Render OHLCV charts with technical indicator overlays.

    Integrates with the terminal's DataClient to fetch real-time and
    historical bar data and render candlestick charts with configurable
    indicator overlays (SMA, EMA, RSI, MACD, Bollinger Bands, etc.).

    Parameters
    ----------
    data_client:
        Instance of ``apps.terminal.data_client.DataClient`` used to
        fetch market data. If ``None``, the panel operates in offline mode.
    """

    def __init__(self, data_client: Any = None) -> None:
        self._data_client = data_client
        self._state = ChartState()
        logger.info("ChartPanel initialized (data_client=%s)", type(data_client).__name__ if data_client else "None")

    @property
    def symbol(self) -> str:
        """Currently displayed symbol."""
        return self._state.symbol

    @property
    def timeframe(self) -> str:
        """Currently displayed timeframe."""
        return self._state.timeframe

    @property
    def indicators(self) -> list[IndicatorConfig]:
        """Active indicator configurations."""
        return list(self._state.indicators)

    async def render_chart(
        self,
        symbol: str,
        timeframe: str = "1D",
        lookback: int = 200,
    ) -> dict[str, Any]:
        """Render an OHLCV chart for the given symbol and timeframe.

        Parameters
        ----------
        symbol:
            Instrument symbol (e.g., ``AAPL``, ``BBCA.JK``).
        timeframe:
            Bar interval string (``1m``, ``5m``, ``1H``, ``1D``, ``1W``).
        lookback:
            Number of bars to fetch.

        Returns
        -------
        dict[str, Any]
            Chart rendering payload with bars and computed indicator series.
        """
        self._state.symbol = symbol
        self._state.timeframe = timeframe

        bars: list[dict[str, Any]] = []
        if self._data_client is not None:
            raw_bars = await self._data_client.get_market_data(
                symbol=symbol,
                timeframe=timeframe,
                limit=lookback,
            )
            bars = raw_bars if isinstance(raw_bars, list) else []
        self._state.last_update = datetime.utcnow()

        indicator_series = self._compute_indicators(bars)

        logger.info("Rendered chart for %s (%s) with %d bars", symbol, timeframe, len(bars))
        return {
            "symbol": symbol,
            "timeframe": timeframe,
            "bars": bars,
            "indicators": indicator_series,
            "bar_count": len(bars),
            "last_update": self._state.last_update.isoformat(),
        }

    def add_indicator(self, name: str, params: dict[str, Any] | None = None, color: str | None = None) -> IndicatorConfig:
        """Add a technical indicator overlay to the chart.

        Parameters
        ----------
        name:
            Indicator name (e.g., ``SMA``, ``EMA``, ``RSI``, ``MACD``, ``BBANDS``).
        params:
            Indicator parameters (e.g., ``{"period": 20}``).
        color:
            Display color hex string.

        Returns
        -------
        IndicatorConfig
            The created indicator configuration.
        """
        config = IndicatorConfig(name=name.upper(), params=params or {}, color=color)
        self._state.indicators.append(config)
        logger.info("Added indicator %s with params=%s", config.name, config.params)
        return config

    async def update_data(self) -> dict[str, Any]:
        """Refresh chart data from the data client.

        Returns
        -------
        dict[str, Any]
            Updated chart rendering payload.

        Raises
        ------
        RuntimeError
            If no symbol has been set via ``render_chart``.
        """
        if not self._state.symbol:
            raise RuntimeError("No symbol set. Call render_chart() first.")
        return await self.render_chart(
            symbol=self._state.symbol,
            timeframe=self._state.timeframe,
        )

    def _compute_indicators(self, bars: list[dict[str, Any]]) -> dict[str, list[float | None]]:
        """Compute indicator series from bar data.

        Parameters
        ----------
        bars:
            List of OHLCV bar dictionaries with ``close`` key.

        Returns
        -------
        dict[str, list[Optional[float]]]
            Mapping of indicator name to computed values.
        """
        closes = [float(b.get("close", 0)) for b in bars]
        results: dict[str, list[float | None]] = {}

        for ind in self._state.indicators:
            if not ind.visible:
                continue
            if ind.name == "SMA":
                period = ind.params.get("period", 20)
                results[f"SMA_{period}"] = self._sma(closes, period)
            elif ind.name == "EMA":
                period = ind.params.get("period", 20)
                results[f"EMA_{period}"] = self._ema(closes, period)
            elif ind.name == "RSI":
                period = ind.params.get("period", 14)
                results[f"RSI_{period}"] = self._rsi(closes, period)
            elif ind.name == "BBANDS":
                period = ind.params.get("period", 20)
                std_dev = ind.params.get("std_dev", 2.0)
                upper, middle, lower = self._bollinger(closes, period, std_dev)
                results[f"BB_UPPER_{period}"] = upper
                results[f"BB_MIDDLE_{period}"] = middle
                results[f"BB_LOWER_{period}"] = lower

        return results

    @staticmethod
    def _sma(data: list[float], period: int) -> list[float | None]:
        """Simple Moving Average."""
        result: list[float | None] = [None] * min(period - 1, len(data))
        for i in range(period - 1, len(data)):
            result.append(sum(data[i - period + 1 : i + 1]) / period)
        return result

    @staticmethod
    def _ema(data: list[float], period: int) -> list[float | None]:
        """Exponential Moving Average."""
        if len(data) < period:
            return [None] * len(data)
        multiplier = 2.0 / (period + 1)
        result: list[float | None] = [None] * (period - 1)
        ema_val = sum(data[:period]) / period
        result.append(ema_val)
        for i in range(period, len(data)):
            ema_val = (data[i] - ema_val) * multiplier + ema_val
            result.append(ema_val)
        return result

    @staticmethod
    def _rsi(data: list[float], period: int) -> list[float | None]:
        """Relative Strength Index."""
        if len(data) < period + 1:
            return [None] * len(data)
        deltas = [data[i] - data[i - 1] for i in range(1, len(data))]
        result: list[float | None] = [None] * period

        gains = [max(d, 0) for d in deltas[:period]]
        losses = [abs(min(d, 0)) for d in deltas[:period]]
        avg_gain = sum(gains) / period
        avg_loss = sum(losses) / period

        if avg_loss == 0:
            result.append(100.0)
        else:
            rs = avg_gain / avg_loss
            result.append(100.0 - (100.0 / (1.0 + rs)))

        for i in range(period, len(deltas)):
            gain = max(deltas[i], 0)
            loss = abs(min(deltas[i], 0))
            avg_gain = (avg_gain * (period - 1) + gain) / period
            avg_loss = (avg_loss * (period - 1) + loss) / period
            if avg_loss == 0:
                result.append(100.0)
            else:
                rs = avg_gain / avg_loss
                result.append(100.0 - (100.0 / (1.0 + rs)))

        return result

    @staticmethod
    def _bollinger(
        data: list[float], period: int, std_dev: float = 2.0
    ) -> tuple[list[float | None], list[float | None], list[float | None]]:
        """Bollinger Bands (upper, middle, lower)."""
        upper: list[float | None] = [None] * min(period - 1, len(data))
        middle: list[float | None] = [None] * min(period - 1, len(data))
        lower: list[float | None] = [None] * min(period - 1, len(data))
        for i in range(period - 1, len(data)):
            window = data[i - period + 1 : i + 1]
            mean = sum(window) / period
            variance = sum((x - mean) ** 2 for x in window) / period
            std = variance**0.5
            middle.append(mean)
            upper.append(mean + std_dev * std)
            lower.append(mean - std_dev * std)
        return upper, middle, lower


__all__ = [
    "ChartPanel",
    "ChartState",
    "IndicatorConfig",
]
