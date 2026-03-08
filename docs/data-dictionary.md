# Pyhron Data Dictionary

## Database: PostgreSQL 16 + TimescaleDB

### Schema: public

#### market_ticks (hypertable)
| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| time | TIMESTAMPTZ | NO | Tick timestamp (partition key) |
| symbol | VARCHAR(20) | NO | Instrument symbol (e.g. BBCA.JK) |
| exchange | VARCHAR(10) | NO | Exchange code (default: IDX) |
| open | NUMERIC(18,4) | NO | Open price |
| high | NUMERIC(18,4) | NO | High price |
| low | NUMERIC(18,4) | NO | Low price |
| close | NUMERIC(18,4) | NO | Close price |
| volume | BIGINT | NO | Trade volume |
| source | VARCHAR(20) | YES | Data source (eodhd, yfinance) |
| created_at | TIMESTAMPTZ | NO | Ingestion timestamp |

**Primary Key:** (time, symbol, exchange)
**Indexes:** ix_market_ticks_symbol, ix_market_ticks_exchange

#### instruments
| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| symbol | VARCHAR(20) | NO | Primary key |
| name | VARCHAR(200) | NO | Company name |
| exchange | VARCHAR(10) | NO | Exchange code |
| sector | VARCHAR(100) | YES | GICS sector |
| industry | VARCHAR(100) | YES | GICS industry |
| market_cap | NUMERIC(20,2) | YES | Market capitalization (IDR) |
| is_lq45 | BOOLEAN | NO | LQ45 index constituent |
| listed_date | DATE | YES | IPO date |
| is_active | BOOLEAN | NO | Currently listed |
| created_at | TIMESTAMPTZ | NO | Record creation |
| updated_at | TIMESTAMPTZ | NO | Last update |

#### orders
| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| client_order_id | VARCHAR(64) | NO | Primary key (UUID) |
| strategy_id | VARCHAR(100) | NO | Owning strategy |
| symbol | VARCHAR(20) | NO | Instrument |
| exchange | VARCHAR(10) | NO | Exchange |
| side | order_side_enum | NO | BUY or SELL |
| order_type | order_type_enum | NO | MARKET, LIMIT, STOP, STOP_LIMIT |
| time_in_force | tif_enum | NO | DAY, GTC, IOC, FOK |
| quantity | INTEGER | NO | Ordered quantity (lots) |
| limit_price | NUMERIC(18,4) | YES | Limit price |
| stop_price | NUMERIC(18,4) | YES | Stop trigger price |
| status | order_status_enum | NO | Current lifecycle status |
| broker_order_id | VARCHAR(100) | YES | Broker-assigned ID |
| filled_quantity | INTEGER | NO | Cumulative filled qty |
| avg_fill_price | NUMERIC(18,4) | YES | VWAP of fills |
| commission | NUMERIC(18,4) | YES | Broker commission |
| tax | NUMERIC(18,4) | YES | IDX sell tax (0.1%) |
| created_at | TIMESTAMPTZ | NO | Order creation |
| submitted_at | TIMESTAMPTZ | YES | Sent to broker |
| acknowledged_at | TIMESTAMPTZ | YES | Broker ACK |
| filled_at | TIMESTAMPTZ | YES | Fully filled |
| updated_at | TIMESTAMPTZ | NO | Last update |

#### positions
| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| id | UUID | NO | Primary key |
| strategy_id | VARCHAR(100) | NO | Owning strategy |
| symbol | VARCHAR(20) | NO | Instrument |
| exchange | VARCHAR(10) | NO | Exchange |
| quantity | INTEGER | NO | Current quantity |
| avg_entry_price | NUMERIC(18,4) | NO | Average entry price |
| realized_pnl | NUMERIC(18,4) | NO | Cumulative realized P&L |
| created_at | TIMESTAMPTZ | NO | Position opened |
| updated_at | TIMESTAMPTZ | NO | Last update |

**Unique Constraint:** (strategy_id, symbol, exchange)

#### trades (hypertable)
| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| trade_id | UUID | NO | Primary key |
| client_order_id | VARCHAR(64) | NO | FK to orders |
| trade_time | TIMESTAMPTZ | NO | Execution time (partition key) |
| symbol | VARCHAR(20) | NO | Instrument |
| side | order_side_enum | NO | BUY or SELL |
| quantity | INTEGER | NO | Fill quantity |
| price | NUMERIC(18,4) | NO | Fill price |
| commission | NUMERIC(18,4) | YES | Commission |
| tax | NUMERIC(18,4) | YES | Sell tax |

---

## Kafka Topics

| Topic | Key | Value (Protobuf) | Partitions | Retention |
|-------|-----|-------------------|------------|-----------|
| pyhron.signals | strategy_id | Signal | 6 | 7d |
| pyhron.orders.risk-decisions | client_order_id | RiskDecision | 6 | 7d |
| pyhron.orders.events | client_order_id | OrderEvent | 12 | 30d |
| pyhron.positions.events | strategy_id | PositionEvent | 6 | 30d |
| pyhron.risk.breaches | strategy_id | RiskBreachEvent | 3 | 90d |
| pyhron.market-data.ticks | symbol | Tick | 12 | 1d |
| pyhron.market-data.bars | symbol | OHLCVBar | 6 | 7d |
| pyhron.dlq.* | (original key) | (original value) | 1 | 30d |

---

## Redis Keys

| Key Pattern | Type | TTL | Description |
|-------------|------|-----|-------------|
| pyhron:risk:circuit_breaker:{strategy_id} | STRING | none | Circuit breaker flag |
| pyhron:risk:recent_orders | LIST | 300s | Recent order IDs for dedup |
| pyhron:ingestion:rate_limit:{source} | STRING | 60s | API rate limit counter |

---

## Enum Types

### order_status_enum
PENDING_RISK → RISK_APPROVED → SUBMITTED → ACKNOWLEDGED → PARTIAL_FILL → FILLED
(also: RISK_REJECTED, REJECTED, CANCELLED, EXPIRED)

### order_side_enum
BUY, SELL

### order_type_enum
MARKET, LIMIT, STOP, STOP_LIMIT
