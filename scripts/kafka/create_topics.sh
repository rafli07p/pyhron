#!/bin/bash
set -e

KAFKA_BOOTSTRAP=kafka:9092
PARTITIONS=3
REPLICATION=1

topics=(
  "pyhron.raw.eod_ohlcv"
  "pyhron.validated.eod_ohlcv"
  "pyhron.raw.fundamentals"
  "pyhron.validated.fundamentals"
  "pyhron.raw.corporate_actions"
  "pyhron.raw.instrument_universe"
  "pyhron.raw.macro_indicators"
  "pyhron.raw.commodity_prices"
  "pyhron.raw.news_articles"
  "pyhron.dlq.eod_ohlcv"
  "pyhron.dlq.fundamentals"
  "pyhron.dlq.corporate_actions"
  "pyhron.orders.order_submitted"
  "pyhron.orders.order_filled"
  "pyhron.portfolio.position_updated"
  "pyhron.strategy.signals.momentum"
  "pyhron.strategy.signals.ml"
  "pyhron.paper.session_started"
  "pyhron.paper.session_stopped"
  "pyhron.paper.nav_snapshot"
  "pyhron.paper.rebalance_result"
  "pyhron.risk.snapshot"
  "pyhron.risk.kill_switch_triggered"
  "pyhron.risk.kill_switch_reset"
  "pyhron.live.activated"
)

for topic in "${topics[@]}"; do
  kafka-topics --bootstrap-server $KAFKA_BOOTSTRAP \
    --create --if-not-exists \
    --topic "$topic" \
    --partitions $PARTITIONS \
    --replication-factor $REPLICATION
  echo "Created topic: $topic"
done
