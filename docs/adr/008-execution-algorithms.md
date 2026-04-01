# ADR-008: Execution Algorithms (TWAP, VWAP, POV, IS)

## Status
Accepted

## Context
The platform needed execution algorithms to optimally slice parent orders into
child orders, respecting IDX lot-size constraints and session breaks.

## Decision
Implement four execution algorithms in `pyhron/execution/algorithms/`:

- **TWAP**: Equal time-weighted slicing with IDX session break awareness
- **VWAP**: Volume-weighted slicing using historical or default intraday profiles
- **POV**: Percentage of volume with OJK 25% dominance threshold enforcement
- **IS**: Almgren-Chriss implementation shortfall with analytical optimal trajectory

All algorithms enforce:
- IDX lot size (100 shares) on every child order
- No slices during 11:30-13:30 WIB session break (TWAP/VWAP)
- OJK single-investor dominance threshold (POV)

## Alternatives Considered
1. **Broker smart order routing** — Rejected: insufficient control over IDX-specific constraints
2. **Single TWAP only** — Rejected: insufficient for different execution objectives
3. **External library (e.g. zipline)** — Rejected: IDX-specific rules not supported

## Consequences
- Algorithms registered in `EXECUTION_ALGORITHMS` dict for OMS lookup
- Child orders emitted to Kafka `execution.child_orders` topic
- Almgren-Chriss parameters (gamma, eta) need calibration per IDX sector
