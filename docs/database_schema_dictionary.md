# Pyhron Database Schema Dictionary

**Database:** PostgreSQL 16 + TimescaleDB
**Extensions:** timescaledb, uuid-ossp, pg_stat_statements, btree_gist

---

## Schema Overview

| # | Schema | Purpose | Key Tables |
|---|--------|---------|------------|
| 1 | market_data | OHLCV prices, ticks, instrument metadata | market_ticks, instruments, intraday_bars |
| 2 | trading | Orders, trades, execution lifecycle | orders, trades |
| 3 | risk | Position tracking, risk limits, circuit breaker state | positions, risk_limits, risk_breach_log |
| 4 | macro | Indonesian macroeconomic indicators | macro_indicators, macro_observations, policy_events |
| 5 | commodity | Commodity price data (CPO, coal, nickel, crude) | commodity_codes, commodity_prices |
| 6 | alternative_data | Satellite, weather, sentiment | fire_hotspots, climate_indices, news_sentiment |
| 7 | fixed_income | Government & corporate bonds, yield curves | yield_curve_snapshots, yield_curve_points, bond_instruments |
| 8 | governance | Corporate governance filings, ownership | governance_filings, ownership_changes, credit_ratings |
| 9 | audit | System audit trail, data lineage | audit_log, data_lineage |
| 10 | analytics | Materialized views, pre-computed analytics | strategy_performance, factor_exposures |

---

## Schema: market_data

### market_data.market_ticks (hypertable)

| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| time | TIMESTAMPTZ | NO | Tick/bar timestamp (partition key) |
| symbol | VARCHAR(20) | NO | Instrument symbol (e.g., BBCA) |
| exchange | VARCHAR(10) | NO | Exchange code (IDX) |
| open | NUMERIC(18,4) | NO | Open price |
| high | NUMERIC(18,4) | NO | High price |
| low | NUMERIC(18,4) | NO | Low price |
| close | NUMERIC(18,4) | NO | Close price |
| volume | BIGINT | NO | Trade volume |
| source | VARCHAR(20) | YES | Data provider (eodhd, yfinance) |
| created_at | TIMESTAMPTZ | NO | Ingestion timestamp |

**Primary Key:** (time, symbol, exchange)
**Chunk Interval:** 7 days
**Compression:** Enabled after 30 days (segment by symbol, order by time)

### market_data.instruments

| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| symbol | VARCHAR(20) | NO | Primary key |
| name | VARCHAR(200) | NO | Company / instrument name |
| exchange | VARCHAR(10) | NO | Exchange code |
| sector | VARCHAR(100) | YES | GICS sector classification |
| industry | VARCHAR(100) | YES | GICS industry |
| market_cap | NUMERIC(20,2) | YES | Market capitalization (IDR) |
| is_lq45 | BOOLEAN | NO | LQ45 index constituent flag |
| listed_date | DATE | YES | IPO / listing date |
| is_active | BOOLEAN | NO | Currently listed |
| created_at | TIMESTAMPTZ | NO | Record creation |
| updated_at | TIMESTAMPTZ | NO | Last update |

### market_data.intraday_bars (hypertable)

| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| time | TIMESTAMPTZ | NO | Bar timestamp (partition key) |
| symbol | VARCHAR(20) | NO | Instrument symbol |
| exchange | VARCHAR(10) | NO | Exchange code |
| interval | VARCHAR(5) | NO | Bar interval (5m, 15m, 1h) |
| open | NUMERIC(18,4) | NO | Open price |
| high | NUMERIC(18,4) | NO | High price |
| low | NUMERIC(18,4) | NO | Low price |
| close | NUMERIC(18,4) | NO | Close price |
| volume | BIGINT | NO | Volume |
| vwap | NUMERIC(18,4) | YES | Volume-weighted average price |
| source | VARCHAR(20) | YES | Data provider |

**Primary Key:** (time, symbol, exchange, interval)
**Chunk Interval:** 1 day

---

## Schema: trading

### trading.orders

| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| client_order_id | VARCHAR(64) | NO | Primary key (UUID v4) |
| strategy_id | VARCHAR(100) | NO | Owning strategy |
| symbol | VARCHAR(20) | NO | Instrument symbol |
| exchange | VARCHAR(10) | NO | Exchange code |
| side | order_side_enum | NO | BUY or SELL |
| order_type | order_type_enum | NO | MARKET, LIMIT, STOP, STOP_LIMIT |
| time_in_force | tif_enum | NO | DAY, GTC, IOC, FOK |
| quantity | INTEGER | NO | Ordered quantity (shares, must be multiple of lot_size) |
| limit_price | NUMERIC(18,4) | YES | Limit price (required for LIMIT, STOP_LIMIT) |
| stop_price | NUMERIC(18,4) | YES | Stop trigger price |
| status | order_status_enum | NO | Current lifecycle status |
| broker_order_id | VARCHAR(100) | YES | Broker-assigned ID |
| filled_quantity | INTEGER | NO | Cumulative filled quantity |
| avg_fill_price | NUMERIC(18,4) | YES | Volume-weighted average fill price |
| commission | NUMERIC(18,4) | YES | Total broker commission |
| tax | NUMERIC(18,4) | YES | IDX sell tax (0.1%) |
| created_at | TIMESTAMPTZ | NO | Order creation timestamp |
| submitted_at | TIMESTAMPTZ | YES | Sent to broker |
| acknowledged_at | TIMESTAMPTZ | YES | Broker acknowledgement |
| filled_at | TIMESTAMPTZ | YES | Fully filled timestamp |
| updated_at | TIMESTAMPTZ | NO | Last status update |

**Indexes:** ix_orders_strategy_id, ix_orders_symbol, ix_orders_status

### trading.trades (hypertable)

| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| trade_id | UUID | NO | Primary key |
| client_order_id | VARCHAR(64) | NO | FK to trading.orders |
| trade_time | TIMESTAMPTZ | NO | Execution time (partition key) |
| symbol | VARCHAR(20) | NO | Instrument symbol |
| side | order_side_enum | NO | BUY or SELL |
| quantity | INTEGER | NO | Fill quantity |
| price | NUMERIC(18,4) | NO | Fill price |
| commission | NUMERIC(18,4) | YES | Commission for this fill |
| tax | NUMERIC(18,4) | YES | Tax for this fill |

**Chunk Interval:** 7 days

---

## Schema: risk

### risk.positions

| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| id | UUID | NO | Primary key |
| strategy_id | VARCHAR(100) | NO | Owning strategy |
| symbol | VARCHAR(20) | NO | Instrument symbol |
| exchange | VARCHAR(10) | NO | Exchange code |
| quantity | INTEGER | NO | Current position quantity |
| avg_entry_price | NUMERIC(18,4) | NO | Volume-weighted average entry price |
| realized_pnl | NUMERIC(18,4) | NO | Cumulative realized P&L (IDR) |
| created_at | TIMESTAMPTZ | NO | Position opened |
| updated_at | TIMESTAMPTZ | NO | Last update |

**Unique Constraint:** (strategy_id, symbol, exchange)

### risk.risk_limits

| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| id | UUID | NO | Primary key |
| strategy_id | VARCHAR(100) | NO | Target strategy (or '*' for global) |
| limit_type | risk_limit_type_enum | NO | Limit category |
| limit_value | NUMERIC(18,6) | NO | Threshold value |
| is_active | BOOLEAN | NO | Enabled flag |
| created_at | TIMESTAMPTZ | NO | Record creation |
| updated_at | TIMESTAMPTZ | NO | Last update |

### risk.risk_breach_log (hypertable)

| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| breach_id | UUID | NO | Primary key |
| breach_time | TIMESTAMPTZ | NO | Partition key |
| strategy_id | VARCHAR(100) | NO | Strategy that breached |
| symbol | VARCHAR(20) | YES | Relevant symbol (if applicable) |
| limit_type | risk_limit_type_enum | NO | Which limit was breached |
| limit_value | NUMERIC(18,6) | NO | Configured threshold |
| actual_value | NUMERIC(18,6) | NO | Actual value at breach time |
| action_taken | VARCHAR(50) | NO | ORDER_REJECTED, TRADING_HALTED, ALERT_ONLY |

---

## Schema: macro

### macro.macro_indicators

| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| indicator_code | VARCHAR(50) | NO | Primary key (e.g., BI_RATE, CPI_YOY) |
| indicator_name | VARCHAR(200) | NO | Human-readable name |
| source | VARCHAR(50) | NO | Publishing institution |
| frequency | VARCHAR(20) | NO | DAILY, WEEKLY, MONTHLY, QUARTERLY, POLICY_MEETING |
| unit | VARCHAR(30) | NO | percent, idr, usd, index, usd_bn |
| description | TEXT | YES | Detailed description |
| is_active | BOOLEAN | NO | Currently tracked |

### macro.macro_observations (hypertable)

| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| id | UUID | NO | Primary key |
| indicator_code | VARCHAR(50) | NO | FK to macro.macro_indicators |
| reference_date | TIMESTAMPTZ | NO | Date the observation refers to (partition key) |
| period | VARCHAR(20) | NO | Reporting period (2024-Q3, 2024-11) |
| value | NUMERIC(20,6) | NO | Observation value |
| previous_value | NUMERIC(20,6) | YES | Prior observation |
| published_at | TIMESTAMPTZ | YES | Source publication timestamp |
| ingested_at | TIMESTAMPTZ | NO | Pyhron ingestion timestamp |

### macro.policy_events

| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| event_id | UUID | NO | Primary key |
| event_type | VARCHAR(50) | NO | BI_RATE_DECISION, APBN_REALIZATION |
| title | VARCHAR(300) | NO | Event title |
| description | TEXT | YES | Event details |
| source | VARCHAR(50) | NO | Publishing institution |
| scheduled_at | TIMESTAMPTZ | NO | Scheduled event time |
| expected_impact | VARCHAR(10) | NO | HIGH, MEDIUM, LOW |
| affected_sectors | TEXT[] | YES | Array of sector codes |

---

## Schema: commodity

### commodity.commodity_codes

| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| commodity_code | VARCHAR(30) | NO | Primary key (CPO, COAL_HBA, NICKEL_LME) |
| commodity_name | VARCHAR(200) | NO | Full name |
| currency | VARCHAR(5) | NO | Price currency (USD, MYR) |
| unit | VARCHAR(30) | NO | Price unit (per_ton, per_barrel) |
| source | VARCHAR(50) | NO | Primary data source |
| is_active | BOOLEAN | NO | Currently tracked |

### commodity.commodity_prices (hypertable)

| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| id | UUID | NO | Primary key |
| commodity_code | VARCHAR(30) | NO | FK to commodity.commodity_codes |
| price_date | TIMESTAMPTZ | NO | Price observation date (partition key) |
| price | NUMERIC(18,4) | NO | Price value |
| previous_price | NUMERIC(18,4) | YES | Prior observation |
| change_pct | NUMERIC(10,4) | YES | Percentage change |
| ingested_at | TIMESTAMPTZ | NO | Ingestion timestamp |

---

## Schema: alternative_data

### alternative_data.fire_hotspots (hypertable)

| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| id | UUID | NO | Primary key |
| detection_time | TIMESTAMPTZ | NO | Satellite detection time (partition key) |
| latitude | NUMERIC(10,6) | NO | Latitude |
| longitude | NUMERIC(10,6) | NO | Longitude |
| confidence | VARCHAR(10) | NO | Detection confidence (low, nominal, high) |
| frp | NUMERIC(10,2) | YES | Fire radiative power (MW) |
| satellite | VARCHAR(10) | NO | VIIRS or MODIS |
| province | VARCHAR(100) | YES | Indonesian province |
| nearest_concession | VARCHAR(200) | YES | Nearest plantation concession |

### alternative_data.climate_indices (hypertable)

| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| id | UUID | NO | Primary key |
| index_date | TIMESTAMPTZ | NO | Reference date (partition key) |
| index_code | VARCHAR(20) | NO | ONI, IOD, SOI |
| value | NUMERIC(10,4) | NO | Index value |
| classification | VARCHAR(30) | YES | El Nino, La Nina, Neutral |
| source | VARCHAR(20) | NO | NOAA, BOM |

### alternative_data.news_sentiment

| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| id | UUID | NO | Primary key |
| published_at | TIMESTAMPTZ | NO | Article publication time |
| symbol | VARCHAR(20) | YES | Related instrument (if identified) |
| headline | TEXT | NO | Article headline |
| sentiment_score | NUMERIC(5,4) | NO | Sentiment (-1.0 to 1.0) |
| source | VARCHAR(50) | NO | News source |
| url | TEXT | YES | Article URL |

---

## Schema: fixed_income

### fixed_income.yield_curve_snapshots

| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| snapshot_id | UUID | NO | Primary key |
| curve_date | DATE | NO | Yield curve date |
| two_year_ten_year_spread_bps | NUMERIC(10,2) | YES | 2Y-10Y spread in basis points |
| real_yield_ten_year | NUMERIC(10,4) | YES | 10Y nominal minus CPI YoY |
| spread_vs_us_ten_year_bps | NUMERIC(10,2) | YES | Premium over US Treasury |
| ingested_at | TIMESTAMPTZ | NO | Ingestion timestamp |

### fixed_income.yield_curve_points

| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| id | UUID | NO | Primary key |
| snapshot_id | UUID | NO | FK to yield_curve_snapshots |
| tenor | VARCHAR(5) | NO | 1M, 3M, 6M, 1Y, 2Y, 5Y, 10Y, 20Y, 30Y |
| tenor_months | INTEGER | NO | Numeric tenor for interpolation |
| yield_pct | NUMERIC(10,4) | NO | Yield percentage |
| change_bps | NUMERIC(10,2) | YES | Change vs previous day (basis points) |

### fixed_income.bond_instruments

| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| isin | VARCHAR(20) | NO | Primary key (ISIN code) |
| series | VARCHAR(50) | NO | Bond series (e.g., FR0098) |
| instrument_type | VARCHAR(20) | NO | SUN, SBSN, Corporate |
| issuer | VARCHAR(200) | NO | Issuer name |
| coupon_rate | NUMERIC(8,4) | YES | Annual coupon rate (%) |
| maturity_date | DATE | NO | Maturity date |
| outstanding_amount | NUMERIC(20,2) | YES | Outstanding principal (IDR) |
| credit_rating | VARCHAR(10) | YES | Latest PEFINDO rating |
| is_active | BOOLEAN | NO | Currently outstanding |

---

## Schema: governance

### governance.governance_filings

| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| filing_id | UUID | NO | Primary key |
| symbol | VARCHAR(20) | NO | Issuer stock code |
| filing_type | VARCHAR(50) | NO | ANNUAL_REPORT, MATERIAL_TRANSACTION, RPT |
| filing_date | DATE | NO | Filing date |
| title | VARCHAR(500) | NO | Filing title |
| url | TEXT | YES | Source URL |
| flags | TEXT[] | YES | Governance flags (if any) |
| ingested_at | TIMESTAMPTZ | NO | Ingestion timestamp |

### governance.ownership_changes

| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| id | UUID | NO | Primary key |
| symbol | VARCHAR(20) | NO | Stock code |
| shareholder_name | VARCHAR(300) | NO | Reporting shareholder |
| change_date | DATE | NO | Transaction date |
| shares_before | BIGINT | YES | Holdings before |
| shares_after | BIGINT | NO | Holdings after |
| pct_ownership | NUMERIC(8,4) | NO | Percentage ownership after |
| transaction_type | VARCHAR(30) | NO | ACQUISITION, DISPOSAL, DILUTION |

### governance.credit_ratings

| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| id | UUID | NO | Primary key |
| symbol | VARCHAR(20) | YES | Stock code (null for sovereign) |
| issuer_name | VARCHAR(200) | NO | Rated entity |
| rating_agency | VARCHAR(30) | NO | PEFINDO, Fitch, Moodys |
| rating | VARCHAR(10) | NO | Rating code (idAAA, BBB+) |
| outlook | VARCHAR(20) | NO | STABLE, POSITIVE, NEGATIVE |
| rating_date | DATE | NO | Rating action date |
| previous_rating | VARCHAR(10) | YES | Prior rating |

---

## Schema: audit

### audit.audit_log

| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| id | BIGINT | NO | Primary key (auto-increment) |
| event_time | TIMESTAMPTZ | NO | Event timestamp |
| actor | VARCHAR(100) | NO | User or service that performed the action |
| action | VARCHAR(50) | NO | CREATE, UPDATE, DELETE, EXECUTE |
| resource_type | VARCHAR(50) | NO | Table or resource affected |
| resource_id | VARCHAR(100) | NO | Primary key of affected resource |
| details | JSONB | YES | Change payload (old/new values) |

### audit.data_lineage

| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| id | UUID | NO | Primary key |
| source | VARCHAR(50) | NO | Data source identifier |
| target_schema | VARCHAR(50) | NO | Destination schema |
| target_table | VARCHAR(100) | NO | Destination table |
| rows_ingested | INTEGER | NO | Number of rows written |
| ingestion_start | TIMESTAMPTZ | NO | Job start time |
| ingestion_end | TIMESTAMPTZ | NO | Job end time |
| status | VARCHAR(20) | NO | SUCCESS, PARTIAL, FAILED |
| error_message | TEXT | YES | Error details (if failed) |

---

## Schema: analytics

### analytics.strategy_performance

| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| id | UUID | NO | Primary key |
| strategy_id | VARCHAR(100) | NO | Strategy identifier |
| calc_date | DATE | NO | Calculation date |
| total_return_pct | NUMERIC(12,6) | NO | Cumulative return |
| sharpe_ratio | NUMERIC(10,6) | YES | Annualized Sharpe ratio |
| sortino_ratio | NUMERIC(10,6) | YES | Annualized Sortino ratio |
| max_drawdown_pct | NUMERIC(10,6) | YES | Maximum drawdown |
| win_rate | NUMERIC(6,4) | YES | Winning trade percentage |
| total_trades | INTEGER | NO | Number of trades to date |
| nav | NUMERIC(20,2) | NO | Net asset value (IDR) |

**Unique Constraint:** (strategy_id, calc_date)

### analytics.factor_exposures

| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| id | UUID | NO | Primary key |
| strategy_id | VARCHAR(100) | NO | Strategy identifier |
| calc_date | DATE | NO | Calculation date |
| factor_name | VARCHAR(50) | NO | Factor (momentum, value, size, quality) |
| exposure | NUMERIC(10,6) | NO | Factor loading |
| contribution_pct | NUMERIC(10,6) | YES | Return contribution from factor |

---

## Enum Types

### order_side_enum
`BUY`, `SELL`

### order_type_enum
`MARKET`, `LIMIT`, `STOP`, `STOP_LIMIT`

### tif_enum (Time in Force)
`DAY`, `GTC`, `IOC`, `FOK`

### order_status_enum
`PENDING_RISK` -> `RISK_APPROVED` -> `SUBMITTED` -> `ACKNOWLEDGED` -> `PARTIAL_FILL` -> `FILLED`
(also: `RISK_REJECTED`, `REJECTED`, `CANCELLED`, `EXPIRED`)

### risk_limit_type_enum
`MAX_POSITION_SIZE_PCT`, `MAX_SECTOR_CONCENTRATION`, `DAILY_LOSS_LIMIT`, `MAX_ORDERS_PER_MINUTE`, `MAX_GROSS_EXPOSURE`, `MAX_VAR`, `MIN_LOT_SIZE`, `T2_BUYING_POWER`
