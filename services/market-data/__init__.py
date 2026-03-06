"""Enthropy Market Data Service.

Provides real-time and historical market data ingestion, normalization,
and streaming for the Enthropy quant research platform. Supports multiple
data sources: Polygon.io (Massive), yfinance, CCXT, and Indonesian
exchange (IDX) adapters.
"""

from __future__ import annotations

__all__ = [
    "MarketDataIngestionService",
    "DataNormalizer",
    "StreamingService",
]


def __getattr__(name: str):  # noqa: N807
    """Lazy imports to avoid heavy startup cost."""
    if name == "MarketDataIngestionService":
        from services.market_data.ingestion import MarketDataIngestionService

        return MarketDataIngestionService
    if name == "DataNormalizer":
        from services.market_data.normalization import DataNormalizer

        return DataNormalizer
    if name == "StreamingService":
        from services.market_data.streaming import StreamingService

        return StreamingService
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
