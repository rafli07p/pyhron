"""Fixed income ingestion modules for Indonesian bond market data."""

from fixed_income_ingestion.djppr_sbn_yield_curve_ingestion import DJPPRSBNYieldCurveIngester
from fixed_income_ingestion.idx_corporate_bond_ingestion import IDXCorporateBondIngester
from fixed_income_ingestion.pefindo_credit_rating_ingestion import PEFINDOCreditRatingIngester

__all__ = [
    "DJPPRSBNYieldCurveIngester",
    "IDXCorporateBondIngester",
    "PEFINDOCreditRatingIngester",
]
