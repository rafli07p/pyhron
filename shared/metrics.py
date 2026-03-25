"""Prometheus metrics for Pyhron platform.

All metrics use a shared registry to avoid conflicts with the
default global registry when running tests.
"""

from prometheus_client import CollectorRegistry, Counter, Gauge, Histogram

REGISTRY = CollectorRegistry()

# Data ingestion
records_ingested_total = Counter(
    "pyhron_records_ingested_total",
    "Total records ingested by source and status",
    ["source", "status"],
    registry=REGISTRY,
)

ingestion_duration_seconds = Histogram(
    "pyhron_ingestion_duration_seconds",
    "Time to complete one ingestion batch",
    ["task_name"],
    buckets=[1, 5, 10, 30, 60, 120, 300],
    registry=REGISTRY,
)

dlq_depth = Gauge(
    "pyhron_dlq_depth",
    "Number of records in DLQ awaiting processing",
    ["topic"],
    registry=REGISTRY,
)

# OMS
orders_submitted_total = Counter(
    "pyhron_orders_submitted_total",
    "Total orders submitted by side and status",
    ["side", "status"],
    registry=REGISTRY,
)

order_fill_latency_seconds = Histogram(
    "pyhron_order_fill_latency_seconds",
    "Time from order submission to fill confirmation",
    buckets=[0.1, 0.5, 1, 2, 5, 10, 30, 60],
    registry=REGISTRY,
)

# Paper trading
paper_session_nav_idr = Gauge(
    "pyhron_paper_session_nav_idr",
    "Current NAV of paper trading session",
    ["session_id", "session_name"],
    registry=REGISTRY,
)

paper_session_drawdown_pct = Gauge(
    "pyhron_paper_session_drawdown_pct",
    "Current drawdown of paper trading session",
    ["session_id"],
    registry=REGISTRY,
)

paper_session_sharpe_ratio = Gauge(
    "pyhron_paper_session_sharpe_ratio",
    "Current Sharpe ratio of paper trading session",
    ["session_name"],
    registry=REGISTRY,
)

paper_session_win_rate_pct = Gauge(
    "pyhron_paper_session_win_rate_pct",
    "Win rate percentage of paper trading session",
    ["session_name"],
    registry=REGISTRY,
)

paper_session_daily_pnl_idr = Gauge(
    "pyhron_paper_session_daily_pnl_idr",
    "Latest daily P&L of paper trading session in IDR",
    ["session_name"],
    registry=REGISTRY,
)

# Intraday market data
intraday_events_total = Counter(
    "pyhron_intraday_events_total",
    "Total intraday market data events received",
    ["event_type", "symbol"],
    registry=REGISTRY,
)

intraday_publish_errors_total = Counter(
    "pyhron_intraday_publish_errors_total",
    "Total failed Kafka publish attempts for intraday data",
    ["topic"],
    registry=REGISTRY,
)

# WebSocket
ws_active_connections = Gauge(
    "pyhron_ws_active_connections",
    "Number of active WebSocket connections",
    registry=REGISTRY,
)

ws_message_latency_seconds = Histogram(
    "pyhron_ws_message_latency_seconds",
    "Latency from Kafka event to WebSocket delivery",
    buckets=[0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.0],
    registry=REGISTRY,
)

# API
http_request_duration_seconds = Histogram(
    "pyhron_http_request_duration_seconds",
    "HTTP request duration",
    ["method", "endpoint", "status_code"],
    registry=REGISTRY,
)
