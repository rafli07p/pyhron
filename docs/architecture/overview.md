# Enthropy Architecture Overview

## System Design

Enthropy is a production-grade quantitative research and trading platform built as a Python monorepo with domain-driven design. The architecture supports the full trading lifecycle: market data ingestion, signal generation, order execution, risk management, PnL tracking, and compliance reporting.

```
                            ┌─────────────────────────────────┐
                            │        Client Applications       │
                            │  Terminal │ Research │ Admin UI   │
                            └──────────────┬──────────────────┘
                                           │
                            ┌──────────────▼──────────────────┐
                            │        API Gateway (FastAPI)      │
                            │  REST │ WebSocket │ gRPC (future) │
                            │  Auth │ Rate Limit │ CORS         │
                            └──────────────┬──────────────────┘
                                           │
               ┌───────────────────────────┼───────────────────────────┐
               │                           │                           │
  ┌────────────▼────────────┐  ┌───────────▼───────────┐  ┌───────────▼───────────┐
  │     Market Data         │  │   Execution Engine     │  │   Portfolio & PnL     │
  │  • Feed handlers        │  │  • Order router        │  │  • Position tracker   │
  │  • Normalization        │  │  • Risk gateway        │  │  • PnL calculator     │
  │  • Tick cache (Redis)   │  │  • Fill processor      │  │  • NAV computation    │
  │  • Historical store     │  │  • Exchange connectors │  │  • Report generator   │
  └────────────┬────────────┘  └───────────┬───────────┘  └───────────┬───────────┘
               │                           │                           │
  ┌────────────▼────────────┐  ┌───────────▼───────────┐  ┌───────────▼───────────┐
  │     Risk Engine         │  │   Strategy Engine      │  │   Research Platform   │
  │  • Pre-trade checks     │  │  • Signal generation   │  │  • Backtest engine    │
  │  • VaR calculation      │  │  • Momentum            │  │  • Factor analysis    │
  │  • Position limits      │  │  • Mean reversion      │  │  • ML experiment      │
  │  • Drawdown monitor     │  │  • Statistical arb     │  │    tracking (MLflow)  │
  └────────────┬────────────┘  └───────────┬───────────┘  └───────────┬───────────┘
               │                           │                           │
               └───────────────────────────┼───────────────────────────┘
                                           │
               ┌───────────────────────────▼───────────────────────────┐
               │                  Shared Infrastructure                 │
               │  ┌──────────┐ ┌──────────┐ ┌───────────┐ ┌─────────┐ │
               │  │ Schemas  │ │Encryption│ │  Audit    │ │  RBAC   │ │
               │  │(Pydantic)│ │(AES-256) │ │  Trail    │ │  Auth   │ │
               │  └──────────┘ └──────────┘ └───────────┘ └─────────┘ │
               └───────────────────────────────────────────────────────┘
                                           │
               ┌───────────────────────────▼───────────────────────────┐
               │                   Data Platform                        │
               │  ┌──────────┐ ┌──────────┐ ┌───────────┐ ┌─────────┐ │
               │  │PostgreSQL│ │  Redis   │ │  Kafka    │ │  S3     │ │
               │  │(primary) │ │ (cache)  │ │ (events)  │ │(backups)│ │
               │  └──────────┘ └──────────┘ └───────────┘ └─────────┘ │
               └───────────────────────────────────────────────────────┘
```

## Component Interactions

### Data Flow

1. **Market Data Ingestion**
   - External feed (API/WebSocket) -> Feed Handler -> Normalization -> Validation
   - Validated ticks -> Redis (real-time cache, TTL: 60s)
   - Validated ticks -> Kafka topic `enthropy.market_data.ticks`
   - Kafka consumer -> PostgreSQL `market_data.ticks` (partitioned by month)

2. **Order Execution Flow**
   - Strategy signal -> `OrderCreate` schema validation
   - Pre-trade risk check (position limit, VaR, drawdown, concentration, leverage)
   - If passed: Order Router -> Exchange Connector (Alpaca/CCXT/Paper)
   - Execution report -> Fill processor -> Position update -> PnL recalculation
   - All state changes -> Kafka topic `enthropy.orders.events`
   - Audit log entry for compliance

3. **Research Pipeline**
   - Historical data loader (Parquet cache / yfinance / PostgreSQL)
   - Strategy instantiation with configurable parameters
   - Backtest engine: iterate bars -> generate signals -> simulate fills
   - Risk engine validation at each step
   - PnL engine tracks realized/unrealized P&L
   - Result: equity curve, trade log, performance metrics, risk report

4. **Compliance & Reporting**
   - Audit trail: every data mutation logged to `audit.logs`
   - PII encrypted with AES-256-GCM (UU PDP compliance)
   - Automated SEC 13F and OJK daily transaction reports
   - Compliance exports signed with SHA-256 integrity hash

## Key Design Decisions

| Decision | Rationale |
|----------|-----------|
| **Monorepo** | Shared schemas, atomic refactoring, unified CI/CD. Each service is a bounded context ready for extraction. |
| **Async-first** | `asyncio` + `uvloop` throughout for non-blocking I/O. Critical for market data feeds and concurrent order processing. |
| **Multi-tenancy** | All data models include `tenant_id` for client isolation. Enables SaaS deployment model. |
| **AES-256-GCM encryption** | Authenticated encryption for PII and strategy IP. Key derivation per context (user PII, trading data). |
| **Pydantic schemas** | Strict validation at domain boundaries. Shared between services for contract enforcement. |
| **Event sourcing (Kafka)** | All order state transitions published as events. Enables replay, audit, and downstream consumers. |
| **Partitioned time-series** | PostgreSQL table partitioning by month for tick data. Enables efficient range queries and data lifecycle management. |
| **Circuit breakers** | `pybreaker` in execution and external API connectors for fault tolerance. |

## External Integrations

| Service | Library | Purpose |
|---------|---------|---------|
| Massive/Polygon | `polygon` | Primary market data (US equities) |
| Alpaca | `alpaca-py` | Order execution (US equities) |
| yfinance | `yfinance` | Fallback data, IDX Indonesia (.JK) |
| CCXT | `ccxt` | Multi-exchange, crypto |
| MLflow | `mlflow` | ML experiment tracking |
| Prometheus | `prometheus_client` | Metrics export |

## Infrastructure

The platform runs on:
- **Local dev**: Docker Compose (see `infra/docker/docker-compose.yaml`)
- **Staging/Production**: Kubernetes on AWS EKS (see `infra/kubernetes/`)
- **Infrastructure as Code**: Terraform for AWS resources (see `infra/terraform/`)
- **Monitoring**: Prometheus + Grafana (see `infra/monitoring/`)
- **CI/CD**: GitLab CI pipeline with trunk-based deployment (see `infra/ci-cd/pipeline.yaml`)

## Database Schema

```
trading.orders          - Order records with status tracking
trading.fills           - Individual fill records per order
trading.positions       - Current position state per symbol/strategy
market_data.ticks       - Time-series tick data (partitioned monthly)
analytics.daily_pnl     - Aggregated daily P&L per strategy/symbol
risk.snapshots          - Periodic risk state captures
audit.logs              - Immutable audit trail for compliance
```

See `scripts/setup_db.py` for full DDL and `scripts/seed_data.py` for development data.

## Migration Path to Polyrepo / Microservices

The monorepo is designed for eventual extraction into independent services. Each domain module under `src/enthropy/` is a bounded context with clearly defined interfaces:

### Phase 1: Extract Market Data Service
1. Move `market_data/` to its own repository
2. Replace in-process imports with gRPC client
3. Deploy as independent container with dedicated Redis
4. Kafka remains the integration point

### Phase 2: Extract Execution Engine
1. Move `execution/` and `risk/` to separate repository
2. Expose order submission via gRPC + REST
3. Independent scaling based on order volume
4. Dedicated database for order/fill state

### Phase 3: Extract Research Platform
1. Move `backtest/`, `strategy/`, `pnl/` to research repo
2. Long-running backtests run on compute-optimized nodes
3. MLflow integration for experiment tracking
4. Separate data lake for historical analysis

### Migration Guidelines
- Shared schemas (`shared/schemas/`) become a published package (PyPI or private registry)
- Kafka topics provide loose coupling between services
- Each service owns its database (no cross-service DB queries)
- API gateway handles routing, auth, and rate limiting
- Feature flags control gradual migration per service
- Kubernetes namespace isolation during transition (see `infra/kubernetes/namespace.yaml`)
