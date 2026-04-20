"""Equity data ingestion modules for IDX (Indonesia Stock Exchange)."""

from .corporate_actions import IDXEquityCorporateActionIngester
from .eod import IDXEquityEODIngester
from .fundamentals import IDXEquityFundamentalIngester
from .governance_flags import IDXEquityGovernanceFlagIngester
from .index_constituents import IDXEquityIndexConstituentIngester

__all__ = [
    "IDXEquityCorporateActionIngester",
    "IDXEquityEODIngester",
    "IDXEquityFundamentalIngester",
    "IDXEquityGovernanceFlagIngester",
    "IDXEquityIndexConstituentIngester",
]
