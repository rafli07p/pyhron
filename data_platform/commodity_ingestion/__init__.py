"""Commodity price ingestion modules for Indonesia-relevant commodities."""

from commodity_ingestion.cpo_price_mpob_ingestion import CPOPriceMPOBIngester
from commodity_ingestion.coal_hba_price_ingestion import CoalHBAPriceIngester
from commodity_ingestion.nickel_lme_price_ingestion import NickelLMEPriceIngester
from commodity_ingestion.indonesian_crude_price_ingestion import IndonesianCrudePriceIngester
from commodity_ingestion.global_commodity_index_ingestion import GlobalCommodityIndexIngester

__all__ = [
    "CPOPriceMPOBIngester",
    "CoalHBAPriceIngester",
    "NickelLMEPriceIngester",
    "IndonesianCrudePriceIngester",
    "GlobalCommodityIndexIngester",
]
