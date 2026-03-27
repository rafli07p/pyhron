#!/usr/bin/env bash
# Pyhron Kafka Topic Initialization
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

# Market Data
create_topic "pyhron.market.ticks"           12  3600000      # 1 hour
create_topic "pyhron.market.ohlcv.1d"        4   604800000    # 7 days
create_topic "pyhron.market.ohlcv.intraday"  8   86400000     # 24 hours

# Equity Strategy Signals
create_topic "pyhron.equity.strategy-signals" 4   3600000     # 1 hour

# Order Lifecycle (event sourcing — compacted)
create_compacted_topic "pyhron.orders.events"          4  2592000000  # 30 days
create_topic           "pyhron.orders.risk-decisions"   4  3600000     # 1 hour

# Position Events (event sourcing — compacted)
create_compacted_topic "pyhron.positions.events"    4  2592000000  # 30 days
create_topic           "pyhron.positions.snapshots"  2  86400000    # 24 hours

# Risk Events
create_topic "pyhron.risk.breaches"          2  604800000   # 7 days
create_topic "pyhron.risk.circuit-breaker"   1  604800000   # 7 days

# Macro Economic Indicators
create_topic "pyhron.macro.indicator-updates" 2  2592000000  # 30 days
create_topic "pyhron.macro.policy-events"     1  2592000000  # 30 days

# Commodity Prices
create_topic "pyhron.commodity.price-updates"         4  2592000000  # 30 days
create_topic "pyhron.commodity.stock-impact-alerts"    2  604800000   # 7 days

# Alternative Data
create_topic "pyhron.alternative-data.fire-hotspot-events"  2  2592000000  # 30 days
create_topic "pyhron.alternative-data.climate-index-events" 1  2592000000  # 30 days
create_topic "pyhron.alternative-data.news-sentiment-events" 4 604800000   # 7 days

# Fixed Income
create_topic "pyhron.fixed-income.yield-curve-snapshots" 1  2592000000  # 30 days
create_topic "pyhron.fixed-income.bond-price-updates"    2  2592000000  # 30 days

# Governance Intelligence
create_topic "pyhron.governance.flag-events"             1  2592000000  # 30 days
create_topic "pyhron.governance.ownership-change-events"  1  2592000000  # 30 days

# Data Platform
create_topic "pyhron.data.ingestion-status"  2  86400000   # 24 hours
create_topic "pyhron.data.quality-alerts"    2  604800000  # 7 days

# Dead Letter Queues
create_topic "pyhron.dlq.equity-strategy-signals"  1  2592000000  # 30 days
create_topic "pyhron.dlq.equity-order-events"      1  2592000000  # 30 days
create_topic "pyhron.dlq.equity-position-events"   1  2592000000  # 30 days
create_topic "pyhron.dlq.macro-indicator-updates"  1  2592000000  # 30 days
create_topic "pyhron.dlq.commodity-price-updates"  1  2592000000  # 30 days
create_topic "pyhron.dlq.fire-hotspot-events"      1  2592000000  # 30 days

echo "All Kafka topics created successfully"
