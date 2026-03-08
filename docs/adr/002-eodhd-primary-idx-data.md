# ADR-002: EODHD as Primary IDX Data Source

## Status
Accepted

## Context
IDX (Indonesia Stock Exchange) market data is not widely available through major US-centric providers. We need reliable EOD OHLCV, fundamentals, corporate actions, and index constituents for ~800 IDX-listed securities.

## Decision
Use EODHD (eodhistoricaldata.com) as the primary data source for IDX equities, with yfinance as a free-tier fallback for EOD prices.

## Consequences
- **Positive:** EODHD covers IDX with EOD prices, fundamentals, dividends/splits, and financial statements. Affordable API pricing. REST-based, easy to integrate.
- **Negative:** No real-time streaming (EOD only). Rate limits require Redis-based throttling. yfinance fallback is unofficial and may break.
- **Mitigation:** Redis rate limiter in ingestion service. Circuit breaker (35% daily move) validation on ingested data. Structured logging for data quality alerts. Future: add IDX FAST/FIX feed when available.
