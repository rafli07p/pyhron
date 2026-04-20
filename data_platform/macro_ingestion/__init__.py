"""Macroeconomic data ingestion modules for Indonesia."""

from .bi_monetary import BankIndonesiaMonetaryDataIngester
from .bmkg_rainfall import BMKGDailyRainfallIngester
from .bps_stats import BPSStatisticsMacroIngester
from .enso_climate import ENSOClimateIndexIngester
from .esdm_energy import ESDMEnergyProductionIngester
from .kemenkeu_apbn import KemenkeuAPBNRealizationIngester

__all__ = [
    "BMKGDailyRainfallIngester",
    "BPSStatisticsMacroIngester",
    "BankIndonesiaMonetaryDataIngester",
    "ENSOClimateIndexIngester",
    "ESDMEnergyProductionIngester",
    "KemenkeuAPBNRealizationIngester",
]
