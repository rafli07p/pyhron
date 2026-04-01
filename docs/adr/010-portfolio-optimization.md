# ADR-010: Portfolio Optimization (Black-Litterman + HRP)

## Status
Accepted

## Context
Portfolio construction needed to combine quantitative views from the ML
pipeline with market equilibrium, while being robust to estimation error
in the covariance matrix.

## Decision
- **Black-Litterman**: Combines equilibrium returns with XGBRanker views.
  Risk aversion varies by regime (bull=2.5, bear=5.0, sideways=3.5).
  MVO solved via scipy SLSQP with long-only and concentration constraints.
- **HRP**: Hierarchical Risk Parity as a robust alternative. Uses
  Ledoit-Wolf shrinkage covariance and single-linkage clustering.
- **Covariance**: Ledoit-Wolf shrinkage (default) or DCC-GARCH(1,1)
  for time-varying correlation.

IDX constraints enforced always:
- Max weight: 15% per stock (OJK mutual fund analog)
- Long-only: no short positions
- Turnover penalty: 30 bps round-trip realistic cost estimate

## Alternatives Considered
1. **DCC-GARCH only** — Rejected as default: computationally expensive, Ledoit-Wolf sufficient for most cases
2. **Equal-weight only** — Rejected: wastes alpha signals
3. **Risk parity without hierarchy** — Rejected: HRP more robust to estimation noise

## Consequences
- PortfolioOptimizer provides unified interface for all methods
- Rebalance endpoint produces actionable weight vectors with cost estimates
- DCC-GARCH requires `arch` library dependency
