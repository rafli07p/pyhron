"""Research service for the Enthropy trading platform.

Provides backtesting, factor analysis, Monte Carlo simulation, and
dataset construction for quantitative research workflows.
"""

from services.research.backtesting import BacktestEngine
from services.research.dataset_builder import DatasetBuilder
from services.research.factor_engine import FactorEngine
from services.research.simulation import MonteCarloSimulator

__all__ = [
    "BacktestEngine",
    "FactorEngine",
    "MonteCarloSimulator",
    "DatasetBuilder",
]
