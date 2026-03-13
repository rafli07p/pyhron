"""Data source adapters for live ingestion pipeline."""

from data_platform.adapters.eodhd_adapter import (
    EODHDAdapter,
    EODHDAPIError,
    EODHDAuthError,
    EODHDDividendRecord,
    EODHDInstrumentRecord,
    EODHDNotFoundError,
    EODHDOHLCVRecord,
    EODHDRateLimitError,
    EODHDSplitRecord,
)

__all__ = [
    "EODHDAPIError",
    "EODHDAdapter",
    "EODHDAuthError",
    "EODHDDividendRecord",
    "EODHDInstrumentRecord",
    "EODHDNotFoundError",
    "EODHDOHLCVRecord",
    "EODHDRateLimitError",
    "EODHDSplitRecord",
]
