"""Macroeconomic data ingestion modules for Indonesia."""

from .bank_indonesia_monetary_data_ingestion import BankIndonesiaMonetaryDataIngester
from .bmkg_daily_rainfall_ingestion import BMKGDailyRainfallIngester
from .bps_statistics_macro_ingestion import BPSStatisticsMacroIngester
from .enso_climate_index_ingestion import ENSOClimateIndexIngester
from .esdm_energy_production_ingestion import ESDMEnergyProductionIngester
from .kemenkeu_apbn_realization_ingestion import KemenkeuAPBNRealizationIngester

__all__ = [
    "BMKGDailyRainfallIngester",
    "BPSStatisticsMacroIngester",
    "BankIndonesiaMonetaryDataIngester",
    "ENSOClimateIndexIngester",
    "ESDMEnergyProductionIngester",
    "KemenkeuAPBNRealizationIngester",
]
