"""Market data ORM models — DEPRECATED.

This module is deprecated. Import from ``data_platform.database_models`` instead.

Re-exports canonical model classes for backward compatibility only.
"""

from __future__ import annotations

import warnings

warnings.warn(
    "data_platform.models.market is deprecated. Use data_platform.database_models instead.",
    DeprecationWarning,
    stacklevel=2,
)

# Re-export canonical models for backward compatibility
from data_platform.database_models.idx_equity_corporate_action import (
    ActionType,
    IdxEquityCorporateAction as CorporateAction,
)
from data_platform.database_models.idx_equity_computed_ratio import (
    IdxEquityComputedRatio as ComputedRatio,
)
from data_platform.database_models.idx_equity_financial_statement import (
    IdxEquityFinancialStatement as FinancialStatement,
    StatementType,
)
from data_platform.database_models.idx_equity_index_constituent import (
    IdxEquityIndexConstituent as IndexConstituent,
)
from data_platform.database_models.idx_equity_instrument import (
    IdxEquityInstrument as Instrument,
)
from data_platform.database_models.idx_equity_news_article import (
    IdxEquityNewsArticle as NewsArticle,
    SentimentLabel,
)
from data_platform.database_models.idx_equity_ohlcv_tick import (
    IdxEquityOhlcvTick as MarketTick,
)

__all__ = [
    "ActionType",
    "ComputedRatio",
    "CorporateAction",
    "FinancialStatement",
    "IndexConstituent",
    "Instrument",
    "MarketTick",
    "NewsArticle",
    "SentimentLabel",
    "StatementType",
]
