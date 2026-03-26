"""Prometheus metrics definitions.

All services import from here for consistent metric naming.
Naming convention: pyhron_{service}_{metric_name}_{unit}
"""

from __future__ import annotations

from prometheus_client import Counter, Gauge, Histogram

# Risk Engine
RISK_CHECK_DURATION = Histogram(
    "pyhron_risk_check_duration_seconds",
    "Pre-trade risk check latency",
    ["check_name", "result"],
    buckets=[0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5],
)

# Orders
ORDERS_TOTAL = Counter(
    "pyhron_orders_total",
    "Total orders by outcome",
    ["status", "exchange", "strategy_id"],
)

# Positions
# Values should be reported in whole IDR units (no decimals) to minimize float precision loss.
POSITION_PNL = Gauge(
    "pyhron_position_pnl_idr",
    "Current unrealized P&L in IDR",
    ["symbol", "strategy_id"],
)

# Ingestion
INGESTION_ROWS = Counter(
    "pyhron_ingestion_rows_total",
    "Total rows ingested",
    ["source", "symbol", "operation"],
)

DATA_FRESHNESS = Gauge(
    "pyhron_data_freshness_seconds",
    "Seconds since last successful ingestion",
    ["symbol"],
)

# API
API_REQUEST_DURATION = Histogram(
    "pyhron_api_request_duration_seconds",
    "API request latency",
    ["method", "endpoint", "status_code"],
    buckets=[0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0],
)

API_REQUESTS_TOTAL = Counter(
    "pyhron_api_requests_total",
    "Total API requests",
    ["method", "endpoint", "status_code"],
)
