# ADR-007: Point-in-Time Data Access Layer

## Status
Accepted

## Context
The audit report identified look-ahead bias as a critical issue. Strategies querying
OHLCV data without strict `as_of` timestamp boundaries can inadvertently train or
signal on future data, producing unrealistically high backtest returns.

## Decision
Enforce point-in-time data access via `PointInTimeSession` in `data_platform/pit_query.py`.

- All OHLCV queries filter `WHERE timestamp <= as_of`
- Fundamental data queries use `loaded_at` (ingestion time), not `reporting_date`
- `PyhronLookAheadError` raised if `as_of` is in the future
- SQLAlchemy event hooks inject `as_of` into all queries within the session
- `lookforward_leak_detector` flags suspiciously high in-sample Sharpe with negative OOS

## Alternatives Considered
1. **Database views with built-in filters** — Rejected: too rigid, hard to parameterise `as_of` per query
2. **Application-level filtering only** — Rejected: error-prone, relies on developer discipline
3. **Temporal tables (PostgreSQL)** — Considered but adds schema complexity without clear benefit

## Consequences
- All backtest and ML training code must use `PointInTimeSession` or `pit_latest_ohlcv`
- Slight overhead from event hooks on every query (negligible for batch workloads)
- Eliminates a critical class of backtesting bugs
