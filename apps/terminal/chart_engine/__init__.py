"""Chart Engine for the Enthropy Terminal.

Provides chart rendering logic with support for technical indicators
including SMA, EMA, RSI, MACD, and Bollinger Bands. Separates chart
computation from display so it can be used by both the ChartPanel
and research tools.
"""

from __future__ import annotations

import logging
import math
from dataclasses import dataclass, field
from typing import Any, Optional

logger = logging.getLogger(__name__)


@dataclass
class OverlayConfig:
    """Configuration for a price overlay (drawn on the price axis)."""

    name: str
    indicator_type: str  # SMA, EMA, BBANDS
    params: dict[str, Any] = field(default_factory=dict)
    color: str = "#FFFFFF"
    line_width: int = 1
    visible: bool = True


@dataclass
class StudyConfig:
    """Configuration for a study (drawn in a separate sub-chart)."""

    name: str
    indicator_type: str  # RSI, MACD, VOLUME
    params: dict[str, Any] = field(default_factory=dict)
    height_ratio: float = 0.25
    visible: bool = True


@dataclass
class ChartData:
    """Processed chart data ready for rendering."""

    symbol: str = ""
    timeframe: str = "1D"
    timestamps: list[str] = field(default_factory=list)
    opens: list[float] = field(default_factory=list)
    highs: list[float] = field(default_factory=list)
    lows: list[float] = field(default_factory=list)
    closes: list[float] = field(default_factory=list)
    volumes: list[float] = field(default_factory=list)
    overlays: dict[str, list[float | None]] = field(default_factory=dict)
    studies: dict[str, list[float | None] | dict[str, list[float | None]]] = field(default_factory=dict)


class ChartEngine:
    """Chart rendering engine with technical indicator computation.

    Computes OHLCV chart data with overlaid indicators (SMA, EMA,
    Bollinger Bands) and sub-chart studies (RSI, MACD). Designed to
    be used by the ChartPanel for terminal rendering or by research
    tools for programmatic chart generation.
    """

    def __init__(self) -> None:
        self._overlays: list[OverlayConfig] = []
        self._studies: list[StudyConfig] = []
        self._chart_data: ChartData | None = None
        logger.info("ChartEngine initialized")

    def create_chart(
        self,
        bars: list[dict[str, Any]],
        symbol: str = "",
        timeframe: str = "1D",
    ) -> ChartData:
        """Create a chart from OHLCV bar data.

        Parameters
        ----------
        bars:
            List of bar dictionaries with keys ``timestamp``, ``open``,
            ``high``, ``low``, ``close``, ``volume``.
        symbol:
            Instrument symbol for labeling.
        timeframe:
            Bar interval string.

        Returns
        -------
        ChartData
            Processed chart data with extracted OHLCV arrays.
        """
        self._chart_data = ChartData(
            symbol=symbol,
            timeframe=timeframe,
            timestamps=[str(b.get("timestamp", "")) for b in bars],
            opens=[float(b.get("open", 0)) for b in bars],
            highs=[float(b.get("high", 0)) for b in bars],
            lows=[float(b.get("low", 0)) for b in bars],
            closes=[float(b.get("close", 0)) for b in bars],
            volumes=[float(b.get("volume", 0)) for b in bars],
        )
        logger.info("Created chart for %s (%s) with %d bars", symbol, timeframe, len(bars))
        return self._chart_data

    def add_overlay(
        self,
        indicator_type: str,
        params: dict[str, Any] | None = None,
        color: str = "#FFFFFF",
        name: str | None = None,
    ) -> OverlayConfig:
        """Add a price overlay indicator.

        Parameters
        ----------
        indicator_type:
            Indicator type: ``SMA``, ``EMA``, or ``BBANDS``.
        params:
            Indicator parameters (e.g., ``{"period": 20}``).
        color:
            Line color hex string.
        name:
            Display name. Auto-generated if not provided.

        Returns
        -------
        OverlayConfig
            The created overlay configuration.
        """
        params = params or {}
        if name is None:
            period = params.get("period", "")
            name = f"{indicator_type}({period})" if period else indicator_type

        config = OverlayConfig(name=name, indicator_type=indicator_type.upper(), params=params, color=color)
        self._overlays.append(config)
        logger.info("Added overlay: %s", name)
        return config

    def add_study(
        self,
        indicator_type: str,
        params: dict[str, Any] | None = None,
        height_ratio: float = 0.25,
        name: str | None = None,
    ) -> StudyConfig:
        """Add a sub-chart study indicator.

        Parameters
        ----------
        indicator_type:
            Study type: ``RSI``, ``MACD``, or ``VOLUME``.
        params:
            Study parameters (e.g., ``{"period": 14}``).
        height_ratio:
            Fraction of total chart height for this study panel.
        name:
            Display name. Auto-generated if not provided.

        Returns
        -------
        StudyConfig
            The created study configuration.
        """
        params = params or {}
        if name is None:
            period = params.get("period", "")
            name = f"{indicator_type}({period})" if period else indicator_type

        config = StudyConfig(name=name, indicator_type=indicator_type.upper(), params=params, height_ratio=height_ratio)
        self._studies.append(config)
        logger.info("Added study: %s", name)
        return config

    def render(self) -> dict[str, Any]:
        """Render the chart with all overlays and studies computed.

        Returns
        -------
        dict[str, Any]
            Complete chart rendering payload.

        Raises
        ------
        RuntimeError
            If no chart data has been created via ``create_chart``.
        """
        if self._chart_data is None:
            raise RuntimeError("No chart data. Call create_chart() first.")

        closes = self._chart_data.closes

        # Compute overlays
        for overlay in self._overlays:
            if not overlay.visible:
                continue
            if overlay.indicator_type == "SMA":
                period = overlay.params.get("period", 20)
                self._chart_data.overlays[overlay.name] = self._compute_sma(closes, period)
            elif overlay.indicator_type == "EMA":
                period = overlay.params.get("period", 20)
                self._chart_data.overlays[overlay.name] = self._compute_ema(closes, period)
            elif overlay.indicator_type == "BBANDS":
                period = overlay.params.get("period", 20)
                std_dev = overlay.params.get("std_dev", 2.0)
                upper, mid, lower = self._compute_bollinger(closes, period, std_dev)
                self._chart_data.overlays[f"{overlay.name}_upper"] = upper
                self._chart_data.overlays[f"{overlay.name}_mid"] = mid
                self._chart_data.overlays[f"{overlay.name}_lower"] = lower

        # Compute studies
        for study in self._studies:
            if not study.visible:
                continue
            if study.indicator_type == "RSI":
                period = study.params.get("period", 14)
                self._chart_data.studies[study.name] = self._compute_rsi(closes, period)
            elif study.indicator_type == "MACD":
                fast = study.params.get("fast_period", 12)
                slow = study.params.get("slow_period", 26)
                signal = study.params.get("signal_period", 9)
                self._chart_data.studies[study.name] = self._compute_macd(closes, fast, slow, signal)
            elif study.indicator_type == "VOLUME":
                self._chart_data.studies[study.name] = self._chart_data.volumes

        result = {
            "symbol": self._chart_data.symbol,
            "timeframe": self._chart_data.timeframe,
            "bar_count": len(closes),
            "ohlcv": {
                "timestamps": self._chart_data.timestamps,
                "opens": self._chart_data.opens,
                "highs": self._chart_data.highs,
                "lows": self._chart_data.lows,
                "closes": self._chart_data.closes,
                "volumes": self._chart_data.volumes,
            },
            "overlays": {k: v for k, v in self._chart_data.overlays.items()},
            "studies": {k: v for k, v in self._chart_data.studies.items()},
        }

        logger.info(
            "Rendered chart: %d overlays, %d studies",
            len(self._chart_data.overlays),
            len(self._chart_data.studies),
        )
        return result

    # ------------------------------------------------------------------
    # Indicator computations
    # ------------------------------------------------------------------

    @staticmethod
    def _compute_sma(data: list[float], period: int) -> list[float | None]:
        """Compute Simple Moving Average."""
        result: list[float | None] = [None] * min(period - 1, len(data))
        for i in range(period - 1, len(data)):
            result.append(sum(data[i - period + 1 : i + 1]) / period)
        return result

    @staticmethod
    def _compute_ema(data: list[float], period: int) -> list[float | None]:
        """Compute Exponential Moving Average."""
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
    def _compute_rsi(data: list[float], period: int) -> list[float | None]:
        """Compute Relative Strength Index."""
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
    def _compute_macd(
        data: list[float],
        fast_period: int = 12,
        slow_period: int = 26,
        signal_period: int = 9,
    ) -> dict[str, list[float | None]]:
        """Compute MACD (line, signal, histogram)."""
        fast_ema = ChartEngine._compute_ema(data, fast_period)
        slow_ema = ChartEngine._compute_ema(data, slow_period)

        macd_line: list[float | None] = []
        for f, s in zip(fast_ema, slow_ema):
            if f is not None and s is not None:
                macd_line.append(f - s)
            else:
                macd_line.append(None)

        macd_values = [v for v in macd_line if v is not None]
        signal_line_raw = ChartEngine._compute_ema(macd_values, signal_period) if macd_values else []

        signal_line: list[float | None] = [None] * (len(macd_line) - len(signal_line_raw))
        signal_line.extend(signal_line_raw)

        histogram: list[float | None] = []
        for m, s in zip(macd_line, signal_line):
            if m is not None and s is not None:
                histogram.append(m - s)
            else:
                histogram.append(None)

        return {
            "macd_line": macd_line,
            "signal_line": signal_line,
            "histogram": histogram,
        }

    @staticmethod
    def _compute_bollinger(
        data: list[float],
        period: int = 20,
        std_dev: float = 2.0,
    ) -> tuple[list[float | None], list[float | None], list[float | None]]:
        """Compute Bollinger Bands (upper, middle, lower)."""
        upper: list[float | None] = [None] * min(period - 1, len(data))
        middle: list[float | None] = [None] * min(period - 1, len(data))
        lower: list[float | None] = [None] * min(period - 1, len(data))
        for i in range(period - 1, len(data)):
            window = data[i - period + 1 : i + 1]
            mean = sum(window) / period
            variance = sum((x - mean) ** 2 for x in window) / period
            std = math.sqrt(variance)
            middle.append(mean)
            upper.append(mean + std_dev * std)
            lower.append(mean - std_dev * std)
        return upper, middle, lower


__all__ = [
    "ChartData",
    "ChartEngine",
    "OverlayConfig",
    "StudyConfig",
]
