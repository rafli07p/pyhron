"""Enthropy Strategies Package.

Provides the complete strategy stack: alpha signal generation,
portfolio construction, and live/paper strategy runtime.  Designed
for systematic quant strategies with support for momentum, mean
reversion, and ML-based alpha models.
"""

from __future__ import annotations

__all__ = [
    "BaseAlphaModel",
    "MomentumAlpha",
    "MeanReversionAlpha",
    "MLAlpha",
    "SignalGenerator",
    "PortfolioConstructor",
    "StrategyRuntime",
]


def __getattr__(name: str):  # noqa: N807
    """Lazy imports to avoid heavy startup cost."""
    _map = {
        "BaseAlphaModel": ("strategies.alpha_models", "BaseAlphaModel"),
        "MomentumAlpha": ("strategies.alpha_models", "MomentumAlpha"),
        "MeanReversionAlpha": ("strategies.alpha_models", "MeanReversionAlpha"),
        "MLAlpha": ("strategies.alpha_models", "MLAlpha"),
        "SignalGenerator": ("strategies.signal_generation", "SignalGenerator"),
        "PortfolioConstructor": ("strategies.portfolio_construction", "PortfolioConstructor"),
        "StrategyRuntime": ("strategies.strategy_runtime", "StrategyRuntime"),
    }
    if name in _map:
        import importlib

        module_path, attr = _map[name]
        mod = importlib.import_module(module_path)
        return getattr(mod, attr)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
