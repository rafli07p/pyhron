"""Alternative data ingestion modules for Indonesian market signals."""

from .bkpm_investment_realization_ingestion import BKPMInvestmentRealizationIngester
from .gaikindo_vehicle_sales_ingestion import GaikindoVehicleSalesIngester
from .nasa_firms_fire_hotspot_ingestion import NASAFIRMSFireHotspotIngester
from .panel_harga_pangan_ingestion import PanelHargaPanganIngester

__all__ = [
    "BKPMInvestmentRealizationIngester",
    "GaikindoVehicleSalesIngester",
    "NASAFIRMSFireHotspotIngester",
    "PanelHargaPanganIngester",
]
