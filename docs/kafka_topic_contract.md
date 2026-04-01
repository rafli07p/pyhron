# Kafka Topic Contract

## New Topics

### `pyhron.execution.child_orders`
- **Partitions**: 3
- **Retention**: 1 hour
- **Schema**: `ChildOrderBatch` (Protobuf)
- **Producer**: OMS / Execution Algo Scheduler
- **Consumer**: Execution Engine
- **Description**: Child orders produced by execution algorithms (TWAP, VWAP, POV, IS) for a parent order.

### `pyhron.ml.signals`
- **Partitions**: 3
- **Retention**: 1 hour
- **Schema**: `SignalBatch` (Protobuf)
- **Producer**: ML Signal Pipeline
- **Consumer**: Strategy Engine, Portfolio Optimizer
- **Description**: Batch of ML signal scores for IDX universe stocks.

### `pyhron.ml.regime`
- **Partitions**: 1
- **Retention**: 7 days
- **Schema**: `RegimeUpdate` (Protobuf)
- **Producer**: Regime Classifier
- **Consumer**: Portfolio Optimizer, Risk Engine
- **Description**: Market regime classification updates (bull/bear/sideways).

### `pyhron.portfolio.rebalance`
- **Partitions**: 2
- **Retention**: 7 days
- **Schema**: `RebalanceResult` (Protobuf)
- **Producer**: Portfolio Optimizer
- **Consumer**: OMS, Execution Engine
- **Description**: Portfolio rebalance results with target weights and cost estimates.
