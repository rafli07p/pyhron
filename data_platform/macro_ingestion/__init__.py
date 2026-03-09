"""Macroeconomic data ingestion modules for Indonesia."""

from macro_ingestion.bank_indonesia_monetary_data_ingestion import BankIndonesiaMonetaryDataIngester
from macro_ingestion.bps_statistics_macro_ingestion import BPSStatisticsMacroIngester
from macro_ingestion.kemenkeu_apbn_realization_ingestion import KemenkeuAPBNRealizationIngester
from macro_ingestion.esdm_energy_production_ingestion import ESDMEnergyProductionIngester
from macro_ingestion.bmkg_daily_rainfall_ingestion import BMKGDailyRainfallIngester
from macro_ingestion.enso_climate_index_ingestion import ENSOClimateIndexIngester

__all__ = [
    "BankIndonesiaMonetaryDataIngester",
    "BPSStatisticsMacroIngester",
    "KemenkeuAPBNRealizationIngester",
    "ESDMEnergyProductionIngester",
    "BMKGDailyRainfallIngester",
    "ENSOClimateIndexIngester",
]
