#!/usr/bin/env bash
# Create all Kafka topics with correct partition and retention settings.
# Idempotent — safe to run multiple times.
#
# Usage (inside Kafka container):
#   KAFKA_BOOTSTRAP_SERVERS=kafka:29092 bash /kafka-topics.sh

set -euo pipefail

BROKER="${KAFKA_BOOTSTRAP_SERVERS:-localhost:9092}"

create_topic() {
    local topic=$1
    local partitions=$2
    local retention_ms=$3

    kafka-topics --bootstrap-server "$BROKER" \
        --create \
        --if-not-exists \
        --topic "$topic" \
        --partitions "$partitions" \
        --replication-factor 1 \
        --config retention.ms="$retention_ms" \
        --config cleanup.policy=delete
}

create_compacted_topic() {
    local topic=$1
    local partitions=$2
    local retention_ms=$3

    kafka-topics --bootstrap-server "$BROKER" \
        --create \
        --if-not-exists \
        --topic "$topic" \
        --partitions "$partitions" \
        --replication-factor 1 \
        --config cleanup.policy=compact \
        --config retention.ms="$retention_ms"
}

echo "Creating Kafka topics on broker: $BROKER"

# ── Market Data ─────────────────────────────────────────────────────────────
create_topic "pyhron.market.ticks"         12  3600000      # 1 hour
create_topic "pyhron.market.ohlcv.1d"      4   604800000    # 7 days
create_topic "pyhron.market.ohlcv.intraday" 8  86400000     # 24 hours

# ── Signal Pipeline ─────────────────────────────────────────────────────────
create_topic "pyhron.signals"              4   3600000      # 1 hour

# ── Order Lifecycle (event sourcing — compacted) ────────────────────────────
create_compacted_topic "pyhron.orders.events"          4  2592000000  # 30 days
create_topic           "pyhron.orders.risk-decisions"   4  3600000     # 1 hour

# ── Position Events (event sourcing — compacted) ────────────────────────────
create_compacted_topic "pyhron.positions.events"    4  2592000000  # 30 days
create_topic           "pyhron.positions.snapshots"  2  86400000    # 24 hours

# ── Risk Events ─────────────────────────────────────────────────────────────
create_topic "pyhron.risk.breaches"        2  604800000   # 7 days
create_topic "pyhron.risk.circuit-breaker" 1  604800000   # 7 days

# ── Data Platform ───────────────────────────────────────────────────────────
create_topic "pyhron.data.ingestion-status" 2  86400000   # 24 hours
create_topic "pyhron.data.quality-alerts"   2  604800000  # 7 days

# ── Dead Letter Queues ──────────────────────────────────────────────────────
create_topic "pyhron.dlq.signals"          1  2592000000  # 30 days
create_topic "pyhron.dlq.orders"           1  2592000000  # 30 days
create_topic "pyhron.dlq.positions"        1  2592000000  # 30 days

echo "All Kafka topics created successfully"
