"""Commodity price ingestion modules for Indonesia-relevant commodities."""

from .coal_hba import CoalHBAPriceIngester
from .cpo_mpob import CPOPriceMPOBIngester
from .global_index import GlobalCommodityIndexIngester
from .icp import IndonesianCrudePriceIngester
from .nickel_lme import NickelLMEPriceIngester

__all__ = [
    "CPOPriceMPOBIngester",
    "CoalHBAPriceIngester",
    "GlobalCommodityIndexIngester",
    "IndonesianCrudePriceIngester",
    "NickelLMEPriceIngester",
]
