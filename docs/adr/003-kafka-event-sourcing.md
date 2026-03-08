# ADR-003: Kafka Event Sourcing for Order Lifecycle

## Status
Accepted

## Context
The order lifecycle involves multiple services (risk engine, OMS, broker adapters, reconciliation). We need a reliable, ordered event log that serves as the source of truth for order state transitions, supports replay for debugging, and decouples producers from consumers.

## Decision
Use Apache Kafka (Confluent cp-kafka:7.6.0 with Zookeeper) as the event backbone. All order state transitions are published as protobuf-encoded events to `pyhron.orders.events`. Risk decisions go to `pyhron.orders.risk-decisions`. Failed messages route to dedicated DLQ topics.

## Consequences
- **Positive:** Immutable event log enables full replay and audit trail. Decoupled services — adding a new consumer doesn't modify producers. Partitioned by `client_order_id` for ordering guarantees per order. Idempotent producers prevent duplicates.
- **Negative:** Operational complexity (Zookeeper + Kafka). Eventually consistent — consumers may lag. Topic management requires init scripts.
- **Mitigation:** kafka-init sidecar creates all topics on startup. DLQ topics for poisoned messages. Consumer lag monitoring via Prometheus. Manual commit mode prevents message loss.
