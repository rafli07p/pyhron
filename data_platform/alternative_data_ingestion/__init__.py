"""Alternative data ingestion modules for Indonesian market signals."""

from .bkpm_investment import BKPMInvestmentRealizationIngester
from .food_prices import PanelHargaPanganIngester
from .gaikindo_sales import GaikindoVehicleSalesIngester
from .nasa_fire_hotspot import NASAFIRMSFireHotspotIngester

__all__ = [
    "BKPMInvestmentRealizationIngester",
    "GaikindoVehicleSalesIngester",
    "NASAFIRMSFireHotspotIngester",
    "PanelHargaPanganIngester",
]
