"""Fixed income ingestion modules for Indonesian bond market data."""

from .djppr_sbn_yield_curve_ingestion import DJPPRSBNYieldCurveIngester
from .idx_corporate_bond_ingestion import IDXCorporateBondIngester
from .pefindo_credit_rating_ingestion import PEFINDOCreditRatingIngester

__all__ = [
    "DJPPRSBNYieldCurveIngester",
    "IDXCorporateBondIngester",
    "PEFINDOCreditRatingIngester",
]
