"""Commodity price ingestion modules for Indonesia-relevant commodities."""

from .coal_hba_price_ingestion import CoalHBAPriceIngester
from .cpo_price_mpob_ingestion import CPOPriceMPOBIngester
from .global_commodity_index_ingestion import GlobalCommodityIndexIngester
from .indonesian_crude_price_ingestion import IndonesianCrudePriceIngester
from .nickel_lme_price_ingestion import NickelLMEPriceIngester

__all__ = [
    "CPOPriceMPOBIngester",
    "CoalHBAPriceIngester",
    "GlobalCommodityIndexIngester",
    "IndonesianCrudePriceIngester",
    "NickelLMEPriceIngester",
]
