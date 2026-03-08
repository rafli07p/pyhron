# ADR-001: TimescaleDB for Market Data Storage

## Status
Accepted

## Context
Pyhron requires efficient storage and querying of time-series market data (OHLCV bars, ticks, trades) for IDX equities. We need sub-second query performance for backtesting over years of data, automatic data retention policies, and native PostgreSQL compatibility for our existing tooling.

## Decision
Use TimescaleDB (latest-pg16) as our primary market data store, leveraging hypertables for `market_ticks` and `trades` tables with automatic time-based partitioning.

## Consequences
- **Positive:** Automatic chunk-based partitioning, compression, and retention policies. Native SQL — no new query language. Continuous aggregates for pre-computed OHLCV rollups. PostgreSQL ecosystem (Alembic, SQLAlchemy, pg_stat_statements).
- **Negative:** Additional operational complexity vs plain PostgreSQL. Hypertable limitations (no unique constraints across chunks without including time column). Extension version coupling.
- **Mitigation:** Use composite primary keys (time + symbol + exchange). Pin TimescaleDB version in docker-compose.
