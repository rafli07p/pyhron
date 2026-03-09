"""Pyhron Strategy Engine — IDX equity trading strategies.

Public API for the strategy engine package.  Import strategies and
supporting infrastructure from this module:

Usage::

    from strategy_engine import (
        BaseStrategyInterface,
        IDXMomentumCrossSectionStrategy,
        IDXBollingerMeanReversionStrategy,
        IDXPairsCointegrationStrategy,
        IDXValueFactorStrategy,
        IDXSectorRotationStrategy,
    )
"""

from strategy_engine.base_strategy_interface import (
    BarData,
    BaseStrategyInterface,
    SignalDirection,
    StrategyParameters,
    StrategySignal,
    TickData,
)
from strategy_engine.idx_bollinger_mean_reversion_strategy import (
    IDXBollingerMeanReversionStrategy,
)
from strategy_engine.idx_momentum_cross_section_strategy import (
    IDXMomentumCrossSectionStrategy,
)
from strategy_engine.idx_pairs_cointegration_strategy import (
    IDXPairsCointegrationStrategy,
)
from strategy_engine.idx_sector_rotation_strategy import (
    IDXSectorRotationStrategy,
)
from strategy_engine.idx_value_factor_strategy import (
    IDXValueFactorStrategy,
)

__all__ = [
    "BarData",
    # Base
    "BaseStrategyInterface",
    # Strategies
    "IDXBollingerMeanReversionStrategy",
    "IDXMomentumCrossSectionStrategy",
    "IDXPairsCointegrationStrategy",
    "IDXSectorRotationStrategy",
    "IDXValueFactorStrategy",
    "SignalDirection",
    "StrategyParameters",
    "StrategySignal",
    "TickData",
]
