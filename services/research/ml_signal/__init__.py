"""ML Signal Layer for Pyhron IDX trading platform.

Provides production-grade ML-based signal generation:
- Feature engineering (7 factor groups, 40+ features)
- Label construction with rank-normalized forward returns
- Purged cross-validation (Lopez de Prado 2018)
- LightGBM cross-sectional alpha model
- LSTM momentum decomposition
- Dynamic IC-weighted signal combination
- MLflow experiment tracking with deployment gates
- Live inference pipeline with SHAP explanations

Imports are lazy to avoid pulling in heavy dependencies (torch, mlflow, shap)
when only lightweight modules are needed.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from services.research.ml_signal.idx_feature_builder import IDXFeatureBuilder as IDXFeatureBuilder
    from services.research.ml_signal.idx_label_builder import IDXLabelBuilder as IDXLabelBuilder
    from services.research.ml_signal.idx_lgbm_alpha_model import IDXLGBMAlphaModel as IDXLGBMAlphaModel
    from services.research.ml_signal.idx_live_inference_engine import (
        IDXLiveInferenceEngine as IDXLiveInferenceEngine,
    )
    from services.research.ml_signal.idx_lstm_momentum_model import (
        IDXLSTMMomentumModel as IDXLSTMMomentumModel,
    )
    from services.research.ml_signal.idx_lstm_momentum_model import IDXLSTMTrainer as IDXLSTMTrainer
    from services.research.ml_signal.idx_model_explainer import IDXModelExplainer as IDXModelExplainer
    from services.research.ml_signal.idx_signal_combiner import IDXSignalCombiner as IDXSignalCombiner
    from services.research.ml_signal.purged_kfold import PurgedKFold as PurgedKFold
    from services.research.ml_signal.pyhron_mlflow_manager import PyhronMLflowManager as PyhronMLflowManager

__all__ = [
    "IDXFeatureBuilder",
    "IDXLabelBuilder",
    "IDXLGBMAlphaModel",
    "IDXLSTMMomentumModel",
    "IDXLSTMTrainer",
    "IDXSignalCombiner",
    "PyhronMLflowManager",
    "IDXLiveInferenceEngine",
    "IDXModelExplainer",
    "PurgedKFold",
]


def __getattr__(name: str) -> object:
    """Lazy import for heavy dependencies."""
    _imports = {
        "IDXFeatureBuilder": "services.research.ml_signal.idx_feature_builder",
        "IDXLabelBuilder": "services.research.ml_signal.idx_label_builder",
        "IDXLGBMAlphaModel": "services.research.ml_signal.idx_lgbm_alpha_model",
        "IDXLSTMMomentumModel": "services.research.ml_signal.idx_lstm_momentum_model",
        "IDXLSTMTrainer": "services.research.ml_signal.idx_lstm_momentum_model",
        "IDXSignalCombiner": "services.research.ml_signal.idx_signal_combiner",
        "PyhronMLflowManager": "services.research.ml_signal.pyhron_mlflow_manager",
        "IDXLiveInferenceEngine": "services.research.ml_signal.idx_live_inference_engine",
        "IDXModelExplainer": "services.research.ml_signal.idx_model_explainer",
        "PurgedKFold": "services.research.ml_signal.purged_kfold",
    }
    if name in _imports:
        import importlib

        module = importlib.import_module(_imports[name])
        return getattr(module, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
