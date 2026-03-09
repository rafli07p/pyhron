# Pyhron Kafka Topic Contract Reference

All Kafka topics, their protobuf message contracts, partition keys, retention policies, and consumer groups. Topics are created by `infra/kafka_topic_initialization.sh`.

---

## Market Data

| Topic | Protobuf Message | Partition Key | Partitions | Retention | Cleanup Policy |
|-------|-----------------|---------------|------------|-----------|----------------|
| `pyhron.market.ticks` | `pyhron.market_data_realtime.Tick` | `symbol` | 12 | 1 hour | delete |
| `pyhron.market.ohlcv.1d` | `pyhron.market_data_realtime.OHLCVBar` | `symbol` | 4 | 7 days | delete |
| `pyhron.market.ohlcv.intraday` | `pyhron.market_data_realtime.OHLCVBar` | `symbol` | 8 | 24 hours | delete |

**Consumer Groups:**
| Group ID | Topics Consumed | Purpose |
|----------|----------------|---------|
| `market-data-persister` | `pyhron.market.ticks`, `pyhron.market.ohlcv.1d`, `pyhron.market.ohlcv.intraday` | Writes market data to TimescaleDB `market_data` schema |
| `strategy-market-feed` | `pyhron.market.ticks`, `pyhron.market.ohlcv.1d` | Feeds real-time prices to strategy signal generators |
| `risk-market-monitor` | `pyhron.market.ticks` | Monitors IHSG level for circuit breaker triggers |

---

## Equity Strategy Signals

| Topic | Protobuf Message | Partition Key | Partitions | Retention | Cleanup Policy |
|-------|-----------------|---------------|------------|-----------|----------------|
| `pyhron.equity.strategy-signals` | `pyhron.strategy_signals.Signal` | `strategy_id` | 4 | 1 hour | delete |

**Consumer Groups:**
| Group ID | Topics Consumed | Purpose |
|----------|----------------|---------|
| `risk-engine` | `pyhron.equity.strategy-signals` | Evaluates signals against pre-trade risk limits, emits OrderRequest or rejection |

---

## Order Lifecycle

| Topic | Protobuf Message | Partition Key | Partitions | Retention | Cleanup Policy |
|-------|-----------------|---------------|------------|-----------|----------------|
| `pyhron.orders.events` | `pyhron.equity_orders.OrderEvent` | `client_order_id` | 4 | 30 days | compact |
| `pyhron.orders.risk-decisions` | `pyhron.equity_orders.RiskDecision` | `client_order_id` | 4 | 1 hour | delete |

**Consumer Groups:**
| Group ID | Topics Consumed | Purpose |
|----------|----------------|---------|
| `order-router` | `pyhron.orders.risk-decisions` | Routes approved orders to broker API |
| `order-persister` | `pyhron.orders.events` | Persists order state transitions to `trading.orders` |
| `position-updater` | `pyhron.orders.events` | Updates positions on FILLED/PARTIAL_FILL events |

---

## Position Events

| Topic | Protobuf Message | Partition Key | Partitions | Retention | Cleanup Policy |
|-------|-----------------|---------------|------------|-----------|----------------|
| `pyhron.positions.events` | `pyhron.equity_positions.PositionEvent` | `strategy_id` | 4 | 30 days | compact |
| `pyhron.positions.snapshots` | `pyhron.equity_positions.PortfolioSnapshot` | `portfolio_id` | 2 | 24 hours | delete |

**Consumer Groups:**
| Group ID | Topics Consumed | Purpose |
|----------|----------------|---------|
| `position-persister` | `pyhron.positions.events` | Writes position changes to `risk.positions` |
| `analytics-snapshot` | `pyhron.positions.snapshots` | Computes performance metrics for `analytics.strategy_performance` |

---

## Risk Events

| Topic | Protobuf Message | Partition Key | Partitions | Retention | Cleanup Policy |
|-------|-----------------|---------------|------------|-----------|----------------|
| `pyhron.risk.breaches` | `pyhron.pre_trade_risk.RiskBreachEvent` | `strategy_id` | 2 | 7 days | delete |
| `pyhron.risk.circuit-breaker` | `pyhron.pre_trade_risk.CircuitBreakerState` | `(none)` | 1 | 7 days | delete |

**Consumer Groups:**
| Group ID | Topics Consumed | Purpose |
|----------|----------------|---------|
| `risk-breach-persister` | `pyhron.risk.breaches` | Writes breach events to `risk.risk_breach_log` |
| `risk-alerter` | `pyhron.risk.breaches`, `pyhron.risk.circuit-breaker` | Sends alerts via configured notification channels |

---

## Macro Economic Indicators

| Topic | Protobuf Message | Partition Key | Partitions | Retention | Cleanup Policy |
|-------|-----------------|---------------|------------|-----------|----------------|
| `pyhron.macro.indicator-updates` | `pyhron.macro_economic_indicators.MacroIndicatorEvent` | `indicator_code` | 2 | 30 days | delete |
| `pyhron.macro.policy-events` | `pyhron.macro_economic_indicators.PolicyEventNotification` | `event_type` | 1 | 30 days | delete |

**Consumer Groups:**
| Group ID | Topics Consumed | Purpose |
|----------|----------------|---------|
| `macro-persister` | `pyhron.macro.indicator-updates` | Writes observations to `macro.macro_observations` |
| `macro-strategy-feed` | `pyhron.macro.indicator-updates`, `pyhron.macro.policy-events` | Feeds macro data to macro-sensitive strategies |

---

## Commodity Prices

| Topic | Protobuf Message | Partition Key | Partitions | Retention | Cleanup Policy |
|-------|-----------------|---------------|------------|-----------|----------------|
| `pyhron.commodity.price-updates` | `pyhron.macro_economic_indicators.CommodityPriceEvent` | `commodity_code` | 4 | 30 days | delete |
| `pyhron.commodity.stock-impact-alerts` | *(JSON)* | `symbol` | 2 | 7 days | delete |

**Consumer Groups:**
| Group ID | Topics Consumed | Purpose |
|----------|----------------|---------|
| `commodity-persister` | `pyhron.commodity.price-updates` | Writes prices to `commodity.commodity_prices` |
| `commodity-impact-analyzer` | `pyhron.commodity.price-updates` | Evaluates impact on IDX commodity stocks, emits stock-impact-alerts |

---

## Alternative Data

| Topic | Protobuf Message | Partition Key | Partitions | Retention | Cleanup Policy |
|-------|-----------------|---------------|------------|-----------|----------------|
| `pyhron.alternative-data.fire-hotspot-events` | *(JSON)* | `province` | 2 | 30 days | delete |
| `pyhron.alternative-data.climate-index-events` | *(JSON)* | `index_code` | 1 | 30 days | delete |
| `pyhron.alternative-data.news-sentiment-events` | *(JSON)* | `symbol` | 4 | 7 days | delete |

**Consumer Groups:**
| Group ID | Topics Consumed | Purpose |
|----------|----------------|---------|
| `altdata-persister` | `pyhron.alternative-data.fire-hotspot-events`, `pyhron.alternative-data.climate-index-events`, `pyhron.alternative-data.news-sentiment-events` | Persists alternative data to `alternative_data` schema |
| `plantation-risk-monitor` | `pyhron.alternative-data.fire-hotspot-events` | Monitors fire activity near plantation concessions for risk alerts |

---

## Fixed Income

| Topic | Protobuf Message | Partition Key | Partitions | Retention | Cleanup Policy |
|-------|-----------------|---------------|------------|-----------|----------------|
| `pyhron.fixed-income.yield-curve-snapshots` | `pyhron.macro_economic_indicators.YieldCurveSnapshot` | `snapshot_id` | 1 | 30 days | delete |
| `pyhron.fixed-income.bond-price-updates` | *(JSON)* | `isin` | 2 | 30 days | delete |

**Consumer Groups:**
| Group ID | Topics Consumed | Purpose |
|----------|----------------|---------|
| `fixed-income-persister` | `pyhron.fixed-income.yield-curve-snapshots`, `pyhron.fixed-income.bond-price-updates` | Writes to `fixed_income` schema tables |

---

## Governance Intelligence

| Topic | Protobuf Message | Partition Key | Partitions | Retention | Cleanup Policy |
|-------|-----------------|---------------|------------|-----------|----------------|
| `pyhron.governance.flag-events` | *(JSON)* | `symbol` | 1 | 30 days | delete |
| `pyhron.governance.ownership-change-events` | *(JSON)* | `symbol` | 1 | 30 days | delete |

**Consumer Groups:**
| Group ID | Topics Consumed | Purpose |
|----------|----------------|---------|
| `governance-persister` | `pyhron.governance.flag-events`, `pyhron.governance.ownership-change-events` | Writes to `governance` schema tables |

---

## Data Platform

| Topic | Protobuf Message | Partition Key | Partitions | Retention | Cleanup Policy |
|-------|-----------------|---------------|------------|-----------|----------------|
| `pyhron.data.ingestion-status` | *(JSON)* | `source` | 2 | 24 hours | delete |
| `pyhron.data.quality-alerts` | *(JSON)* | `source` | 2 | 7 days | delete |

**Consumer Groups:**
| Group ID | Topics Consumed | Purpose |
|----------|----------------|---------|
| `data-platform-monitor` | `pyhron.data.ingestion-status`, `pyhron.data.quality-alerts` | Powers the data pipeline health dashboard and alerting |

---

## Dead Letter Queues

| Topic | Original Topic | Partitions | Retention |
|-------|---------------|------------|-----------|
| `pyhron.dlq.equity-strategy-signals` | `pyhron.equity.strategy-signals` | 1 | 30 days |
| `pyhron.dlq.equity-order-events` | `pyhron.orders.events` | 1 | 30 days |
| `pyhron.dlq.equity-position-events` | `pyhron.positions.events` | 1 | 30 days |
| `pyhron.dlq.macro-indicator-updates` | `pyhron.macro.indicator-updates` | 1 | 30 days |
| `pyhron.dlq.commodity-price-updates` | `pyhron.commodity.price-updates` | 1 | 30 days |
| `pyhron.dlq.fire-hotspot-events` | `pyhron.alternative-data.fire-hotspot-events` | 1 | 30 days |

DLQ messages retain the original key and value, wrapped with error metadata headers (`x-error-reason`, `x-original-topic`, `x-failed-at`).
