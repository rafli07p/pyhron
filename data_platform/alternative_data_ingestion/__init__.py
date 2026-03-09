"""Alternative data ingestion modules for Indonesian market signals."""

from alternative_data_ingestion.nasa_firms_fire_hotspot_ingestion import NASAFIRMSFireHotspotIngester
from alternative_data_ingestion.gaikindo_vehicle_sales_ingestion import GaikindoVehicleSalesIngester
from alternative_data_ingestion.bkpm_investment_realization_ingestion import BKPMInvestmentRealizationIngester
from alternative_data_ingestion.panel_harga_pangan_ingestion import PanelHargaPanganIngester

__all__ = [
    "NASAFIRMSFireHotspotIngester",
    "GaikindoVehicleSalesIngester",
    "BKPMInvestmentRealizationIngester",
    "PanelHargaPanganIngester",
]
