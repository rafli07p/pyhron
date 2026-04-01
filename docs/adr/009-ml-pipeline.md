# ADR-009: ML Signal Generation Pipeline

## Status
Accepted

## Context
The platform needed an ML pipeline for alpha signal generation with proper
model lifecycle management and point-in-time safety.

## Decision
- **Feature Store**: Redis-backed with strict PIT boundaries, cross-sectional
  winsorization and z-scoring. Built-in features: momentum, volatility, RSI,
  MACD, volume ratio, Amihud illiquidity, etc.
- **Model Registry**: Thin MLflow wrapper with PIT-safe model loading
  (`load_as_of` prevents using models trained on future data)
- **XGBoost Ranker**: LambdaRank for cross-sectional equity ranking with
  Optuna hyperparameter tuning (20 trials)
- **LSTM Volatility**: 1-day-ahead vol forecasting with ONNX export
- **Regime Classifier**: HMM with 3 states (bull/bear/sideways)

## Alternatives Considered
1. **Custom model registry** — Rejected: MLflow provides experiment tracking, artifact storage, and UI
2. **Feast feature store** — Considered: too heavyweight for current scale; Redis sufficient
3. **Neural ranker instead of XGBoost** — Rejected: XGBoost more interpretable and faster to train

## Consequences
- All models use `pyhron/{name}` experiment naming in MLflow
- Required tags: `idx_universe=true`, `pit_safe=true`
- ONNX export enables fast inference without PyTorch dependency
