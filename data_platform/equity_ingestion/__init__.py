"""Equity data ingestion modules for IDX (Indonesia Stock Exchange)."""

from equity_ingestion.idx_equity_corporate_action_ingestion import IDXEquityCorporateActionIngester
from equity_ingestion.idx_equity_end_of_day_ingestion import IDXEquityEODIngester
from equity_ingestion.idx_equity_fundamental_ingestion import IDXEquityFundamentalIngester
from equity_ingestion.idx_equity_governance_flag_ingestion import IDXEquityGovernanceFlagIngester
from equity_ingestion.idx_equity_index_constituent_ingestion import IDXEquityIndexConstituentIngester

__all__ = [
    "IDXEquityCorporateActionIngester",
    "IDXEquityEODIngester",
    "IDXEquityFundamentalIngester",
    "IDXEquityGovernanceFlagIngester",
    "IDXEquityIndexConstituentIngester",
]
