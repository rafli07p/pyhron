# ADR-006: vectorbt for Backtesting Engine

## Status
Proposed

## Context
Backtesting requires fast vectorized operations over historical OHLCV data. We need a framework that supports custom signal generation, portfolio simulation with IDX-specific constraints (lot size, T+2 settlement, sell tax), and integration with MLflow for experiment tracking.

## Decision
Use vectorbt as the backtesting engine, wrapped in a Pyhron-specific adapter that enforces IDX constraints (lot_size=100, 0.1% sell tax, T+2 settlement). Results are logged to MLflow for experiment comparison.

## Consequences
- **Positive:** NumPy-based vectorized execution — orders of magnitude faster than event-driven backtesters. Built-in portfolio simulation, metrics (Sharpe, Sortino, max drawdown). Good pandas/NumPy interop.
- **Negative:** Less flexible than event-driven backtesting for complex order types. IDX-specific constraints must be applied as post-processing. Memory-intensive for large universes.
- **Mitigation:** Custom wrapper handles lot sizing and tax. Chunked backtesting for large date ranges. MLflow tracks all parameters and results for reproducibility.
