"""Market data normalization and quality checks.

Converts raw data from Polygon, yfinance, and CCXT into the unified
``shared.schemas.market_events`` models.  Handles timezone conversion
(UTC standard, Jakarta WIB support) and data-quality validation.
"""

from __future__ import annotations

import math
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from typing import Any, Optional, Sequence
from zoneinfo import ZoneInfo

import structlog

from shared.schemas.market_events import (
    BarEvent,
    Exchange,
    QuoteEvent,
    TickEvent,
    TradeEvent,
)

logger = structlog.get_logger(__name__)

# ---------------------------------------------------------------------------
# Timezone helpers
# ---------------------------------------------------------------------------
UTC = timezone.utc
WIB = ZoneInfo("Asia/Jakarta")  # UTC+7  (Western Indonesian Time)


def _to_utc(dt: datetime, source_tz: ZoneInfo | timezone | None = None) -> datetime:
    """Ensure *dt* is in UTC.

    If *dt* is naive it is assumed to be in *source_tz* (default UTC).
    """
    if dt.tzinfo is None:
        tz = source_tz or UTC
        dt = dt.replace(tzinfo=tz)
    return dt.astimezone(UTC)


def _safe_decimal(value: Any, field_name: str = "value") -> Decimal:
    """Convert *value* to ``Decimal``, raising on garbage input."""
    if isinstance(value, Decimal):
        return value
    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError, TypeError) as exc:
        raise ValueError(f"Cannot convert {field_name}={value!r} to Decimal") from exc


# ---------------------------------------------------------------------------
# Data quality issue descriptions
# ---------------------------------------------------------------------------

class DataQualityIssue:
    """Lightweight container for a single data-quality finding."""

    __slots__ = ("level", "field", "message", "value")

    def __init__(self, level: str, field: str, message: str, value: Any = None) -> None:
        self.level = level  # "warning" | "error"
        self.field = field
        self.message = message
        self.value = value

    def __repr__(self) -> str:
        return f"<DQIssue {self.level}: {self.field} - {self.message}>"

    def to_dict(self) -> dict[str, Any]:
        return {
            "level": self.level,
            "field": self.field,
            "message": self.message,
            "value": self.value,
        }


# ---------------------------------------------------------------------------
# DataNormalizer
# ---------------------------------------------------------------------------

class DataNormalizer:
    """Normalize heterogeneous market data into unified Enthropy schemas.

    Parameters
    ----------
    tenant_id:
        Tenant identifier attached to every output event.
    default_source_tz:
        Timezone to assume when raw timestamps are naive.
    outlier_z_threshold:
        Z-score threshold for flagging price outliers in a series.
    """

    def __init__(
        self,
        tenant_id: str,
        default_source_tz: ZoneInfo | timezone = UTC,
        outlier_z_threshold: float = 4.0,
    ) -> None:
        self.tenant_id = tenant_id
        self.default_source_tz = default_source_tz
        self.outlier_z_threshold = outlier_z_threshold
        self._log = logger.bind(tenant_id=tenant_id, service="normalization")

    # ------------------------------------------------------------------
    # Bar normalizers
    # ------------------------------------------------------------------

    def normalize_bar(
        self,
        raw: dict[str, Any],
        source: str = "polygon",
        source_tz: ZoneInfo | timezone | None = None,
    ) -> BarEvent:
        """Normalize a single OHLCV bar from *source* into a ``BarEvent``.

        Supported *source* values: ``polygon``, ``yfinance``, ``ccxt``.
        """
        tz = source_tz or self.default_source_tz

        if source == "polygon":
            return self._bar_from_polygon(raw, tz)
        if source == "yfinance":
            return self._bar_from_yfinance(raw, tz)
        if source == "ccxt":
            return self._bar_from_ccxt(raw, tz)
        raise ValueError(f"Unknown bar source: {source!r}")

    def _bar_from_polygon(self, raw: dict[str, Any], tz: ZoneInfo | timezone) -> BarEvent:
        # Polygon aggregates: t (ms epoch), o, h, l, c, v, vw, n
        ts = datetime.utcfromtimestamp(raw["t"] / 1000).replace(tzinfo=UTC)
        return BarEvent(
            symbol=raw.get("T", raw.get("ticker", "")),
            timestamp=_to_utc(ts, tz),
            exchange=Exchange.OTHER,
            tenant_id=self.tenant_id,
            open=_safe_decimal(raw["o"], "open"),
            high=_safe_decimal(raw["h"], "high"),
            low=_safe_decimal(raw["l"], "low"),
            close=_safe_decimal(raw["c"], "close"),
            volume=_safe_decimal(raw.get("v", 0), "volume"),
            vwap=_safe_decimal(raw["vw"], "vwap") if raw.get("vw") else None,
            bar_count=raw.get("n"),
            interval_seconds=raw.get("interval_seconds", 60),
        )

    def _bar_from_yfinance(self, raw: dict[str, Any], tz: ZoneInfo | timezone) -> BarEvent:
        # yfinance rows: Date/Datetime, Open, High, Low, Close, Volume
        ts_raw = raw.get("Datetime") or raw.get("Date") or raw.get("timestamp")
        if isinstance(ts_raw, str):
            ts = datetime.fromisoformat(ts_raw)
        elif isinstance(ts_raw, datetime):
            ts = ts_raw
        else:
            ts = datetime.utcnow()
        return BarEvent(
            symbol=raw.get("symbol", ""),
            timestamp=_to_utc(ts, tz),
            exchange=Exchange.OTHER,
            tenant_id=self.tenant_id,
            open=_safe_decimal(raw["Open"], "open"),
            high=_safe_decimal(raw["High"], "high"),
            low=_safe_decimal(raw["Low"], "low"),
            close=_safe_decimal(raw["Close"], "close"),
            volume=_safe_decimal(raw.get("Volume", 0), "volume"),
            interval_seconds=86400,
        )

    def _bar_from_ccxt(self, raw: dict[str, Any], tz: ZoneInfo | timezone) -> BarEvent:
        # CCXT OHLCV: list [timestamp_ms, open, high, low, close, volume]
        if isinstance(raw, (list, tuple)):
            ts_ms, o, h, l_, c, v = raw[:6]
            symbol = ""
        else:
            ts_ms = raw["timestamp"]
            o, h, l_, c, v = raw["open"], raw["high"], raw["low"], raw["close"], raw["volume"]
            symbol = raw.get("symbol", "")
        ts = datetime.utcfromtimestamp(ts_ms / 1000).replace(tzinfo=UTC)
        return BarEvent(
            symbol=symbol,
            timestamp=_to_utc(ts, tz),
            exchange=Exchange.OTHER,
            tenant_id=self.tenant_id,
            open=_safe_decimal(o, "open"),
            high=_safe_decimal(h, "high"),
            low=_safe_decimal(l_, "low"),
            close=_safe_decimal(c, "close"),
            volume=_safe_decimal(v, "volume"),
            interval_seconds=raw.get("interval_seconds", 60) if isinstance(raw, dict) else 60,
        )

    # ------------------------------------------------------------------
    # Tick normalizer
    # ------------------------------------------------------------------

    def normalize_tick(
        self,
        raw: dict[str, Any],
        source: str = "polygon",
        source_tz: ZoneInfo | timezone | None = None,
    ) -> TickEvent:
        """Normalize a raw tick into a ``TickEvent``."""
        tz = source_tz or self.default_source_tz

        if source == "polygon":
            # Polygon trade/tick: t (ns epoch), p, s, c
            ts_ns = raw.get("t", raw.get("timestamp", 0))
            ts = datetime.utcfromtimestamp(ts_ns / 1e9).replace(tzinfo=UTC)
            return TickEvent(
                symbol=raw.get("sym", raw.get("T", "")),
                timestamp=_to_utc(ts, tz),
                exchange=Exchange.OTHER,
                tenant_id=self.tenant_id,
                price=_safe_decimal(raw["p"], "price"),
                volume=_safe_decimal(raw.get("s", 0), "volume"),
                condition=",".join(str(c) for c in raw["c"]) if raw.get("c") else None,
            )

        if source == "ccxt":
            ts = datetime.utcfromtimestamp(raw["timestamp"] / 1000).replace(tzinfo=UTC)
            return TickEvent(
                symbol=raw.get("symbol", ""),
                timestamp=_to_utc(ts, tz),
                exchange=Exchange.OTHER,
                tenant_id=self.tenant_id,
                price=_safe_decimal(raw["price"], "price"),
                volume=_safe_decimal(raw.get("amount", 0), "volume"),
            )

        raise ValueError(f"Unknown tick source: {source!r}")

    # ------------------------------------------------------------------
    # Trade normalizer
    # ------------------------------------------------------------------

    def normalize_trade(
        self,
        raw: dict[str, Any],
        source: str = "polygon",
        source_tz: ZoneInfo | timezone | None = None,
    ) -> TradeEvent:
        """Normalize a raw trade into a ``TradeEvent``."""
        tz = source_tz or self.default_source_tz

        if source == "polygon":
            ts_ns = raw.get("t", raw.get("timestamp", 0))
            ts = datetime.utcfromtimestamp(ts_ns / 1e9).replace(tzinfo=UTC)
            return TradeEvent(
                symbol=raw.get("sym", raw.get("T", "")),
                timestamp=_to_utc(ts, tz),
                exchange=Exchange.OTHER,
                tenant_id=self.tenant_id,
                price=_safe_decimal(raw["p"], "price"),
                volume=_safe_decimal(raw["s"], "volume"),
                trade_id=str(raw.get("i", "")),
                aggressor_side=None,
            )

        if source == "ccxt":
            ts = datetime.utcfromtimestamp(raw["timestamp"] / 1000).replace(tzinfo=UTC)
            side_map = {"buy": "BUY", "sell": "SELL"}
            return TradeEvent(
                symbol=raw.get("symbol", ""),
                timestamp=_to_utc(ts, tz),
                exchange=Exchange.OTHER,
                tenant_id=self.tenant_id,
                price=_safe_decimal(raw["price"], "price"),
                volume=_safe_decimal(raw["amount"], "volume"),
                trade_id=raw.get("id"),
                aggressor_side=side_map.get(raw.get("side", ""), "UNKNOWN"),
            )

        raise ValueError(f"Unknown trade source: {source!r}")

    # ------------------------------------------------------------------
    # Quote normalizer (convenience)
    # ------------------------------------------------------------------

    def normalize_quote(
        self,
        raw: dict[str, Any],
        source: str = "polygon",
        source_tz: ZoneInfo | timezone | None = None,
    ) -> QuoteEvent:
        """Normalize a raw quote into a ``QuoteEvent``."""
        tz = source_tz or self.default_source_tz

        if source == "polygon":
            ts_ns = raw.get("t", raw.get("timestamp", 0))
            ts = datetime.utcfromtimestamp(ts_ns / 1e9).replace(tzinfo=UTC)
            return QuoteEvent(
                symbol=raw.get("sym", raw.get("T", "")),
                timestamp=_to_utc(ts, tz),
                exchange=Exchange.OTHER,
                tenant_id=self.tenant_id,
                bid=_safe_decimal(raw["bp"], "bid"),
                ask=_safe_decimal(raw["ap"], "ask"),
                bid_size=_safe_decimal(raw.get("bs", 0), "bid_size"),
                ask_size=_safe_decimal(raw.get("as", 0), "ask_size"),
            )

        raise ValueError(f"Unknown quote source: {source!r}")

    # ------------------------------------------------------------------
    # Data quality validation
    # ------------------------------------------------------------------

    def validate_data_quality(
        self,
        bars: Sequence[BarEvent],
    ) -> list[DataQualityIssue]:
        """Run quality checks on a sequence of bars.

        Checks performed
        ----------------
        1. Missing data detection (gaps > expected interval).
        2. OHLCV validation (high >= low, non-negative volume, etc.).
        3. Outlier flagging based on close-price Z-score.

        Returns
        -------
        list[DataQualityIssue]
            All detected issues (may be empty).
        """
        issues: list[DataQualityIssue] = []
        if not bars:
            return issues

        closes: list[float] = []
        prev_ts: Optional[datetime] = None

        for i, bar in enumerate(bars):
            # --- OHLCV validation ---
            if bar.high < bar.low:
                issues.append(
                    DataQualityIssue(
                        "error", "high/low",
                        f"Bar {i}: high ({bar.high}) < low ({bar.low})",
                        {"high": str(bar.high), "low": str(bar.low)},
                    )
                )
            if bar.volume < 0:
                issues.append(
                    DataQualityIssue(
                        "error", "volume",
                        f"Bar {i}: negative volume ({bar.volume})",
                        str(bar.volume),
                    )
                )
            for field_name in ("open", "high", "low", "close"):
                val = getattr(bar, field_name)
                if val <= 0:
                    issues.append(
                        DataQualityIssue(
                            "error", field_name,
                            f"Bar {i}: non-positive {field_name} ({val})",
                            str(val),
                        )
                    )

            # --- Missing data detection ---
            bar_ts = bar.timestamp if bar.timestamp.tzinfo else bar.timestamp.replace(tzinfo=UTC)
            if prev_ts is not None:
                gap = (bar_ts - prev_ts).total_seconds()
                expected = bar.interval_seconds
                if gap > expected * 2:
                    issues.append(
                        DataQualityIssue(
                            "warning", "timestamp",
                            f"Bar {i}: gap of {gap}s exceeds 2x expected interval ({expected}s)",
                            {"gap_seconds": gap, "expected": expected},
                        )
                    )
            prev_ts = bar_ts

            closes.append(float(bar.close))

        # --- Outlier detection (Z-score on close prices) ---
        if len(closes) >= 10:
            mean = sum(closes) / len(closes)
            variance = sum((c - mean) ** 2 for c in closes) / len(closes)
            std = math.sqrt(variance) if variance > 0 else 0.0
            if std > 0:
                for i, c in enumerate(closes):
                    z = abs(c - mean) / std
                    if z > self.outlier_z_threshold:
                        issues.append(
                            DataQualityIssue(
                                "warning", "close",
                                f"Bar {i}: close={c} is an outlier (z={z:.2f})",
                                {"close": c, "z_score": round(z, 2)},
                            )
                        )

        if issues:
            self._log.warning("data_quality_issues_found", count=len(issues))
        else:
            self._log.debug("data_quality_ok", bar_count=len(bars))

        return issues


__all__ = ["DataNormalizer", "DataQualityIssue"]
