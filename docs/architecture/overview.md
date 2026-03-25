# Pyhron Architecture Overview

## System Design

Pyhron is a production-grade quantitative research and trading platform for the Indonesia Stock Exchange (IDX), built as a Python monorepo. The architecture supports the full trading lifecycle: market data ingestion, signal generation, backtesting, paper trading, order execution, risk management, and compliance reporting.

```
                            ┌─────────────────────────────────┐
                            │        Client Applications       │
                            │  Terminal │ Research │ Dashboard  │
                            └──────────────┬──────────────────┘
                                           │
                            ┌──────────────▼──────────────────┐
                            │        API Gateway (FastAPI)      │
                            │  REST │ WebSocket │ CSRF │ RBAC   │
                            │  JWT Auth │ Rate Limit │ CORS     │
                            └──────────────┬──────────────────┘
                                           │
               ┌───────────────────────────┼───────────────────────────┐
               │                           │                           │
  ┌────────────▼────────────┐  ┌───────────▼───────────┐  ┌───────────▼───────────┐
  │     Market Data         │  │   Execution Engine     │  │   Portfolio & PnL     │
  │  • EODHD EOD ingestion  │  │  • Order lifecycle     │  │  • Position tracker   │
  │  • Alpaca WebSocket     │  │  • Risk gateway        │  │  • PnL attribution    │
  │  • Intraday bars/trades │  │  • Alpaca connector    │  │  • NAV computation    │
  │  • TimescaleDB storage  │  │  • Paper trading       │  │  • Report generator   │
  └────────────┬────────────┘  └───────────┬───────────┘  └───────────┬───────────┘
               │                           │                           │
  ┌────────────▼────────────┐  ┌───────────▼───────────┐  ┌───────────▼───────────┐
  │     Risk Engine         │  │   Strategy Engine      │  │   Research Platform   │
  │  • Pre-trade checks     │  │  • Momentum (12-1)     │  │  • Vectorbt backtest  │
  │  • Position limits      │  │  • Mean reversion      │  │  • Walk-forward       │
  │  • Drawdown monitor     │  │  • Pairs/cointegration │  │  • LightGBM alpha     │
  │  • IDX lot constraints  │  │  • Value factor        │  │  • LSTM momentum      │
  └────────────┬────────────┘  │  • Sector rotation     │  │  • MLflow tracking    │
               │               └───────────┬───────────┘  └───────────┬───────────┘
               │                           │                           │
               └───────────────────────────┼───────────────────────────┘
                                           │
               ┌───────────────────────────▼───────────────────────────┐
               │                  Event Bus (Kafka)                     │
               │  30+ topics: EOD, intraday, orders, signals, DLQ      │
               └───────────────────────────┬───────────────────────────┘
                                           │
               ┌───────────────────────────▼───────────────────────────┐
               │                   Data Platform                        │
               │  ┌──────────┐ ┌──────────┐ ┌───────────┐ ┌─────────┐ │
               │  │TimescaleDB│ │  Redis   │ │Prometheus │ │ Grafana │ │
               │  │(OHLCV +  │ │ (pub/sub │ │ (metrics) │ │(dashbrd)│ │
               │  │ signals) │ │  + cache)│ │           │ │         │ │
               │  └──────────┘ └──────────┘ └───────────┘ └─────────┘ │
               └───────────────────────────────────────────────────────┘
```

## Data Flow

### 1. EOD Market Data Ingestion
```
EODHD API → EOD Ingestion Consumer → Kafka (raw.eod_ohlcv)
  → Validation Consumer → Kafka (validated.eod_ohlcv)
  → TimescaleDB Writer → market_data.idx_equity_ohlcv_tick
  → Kafka→Redis Bridge → WebSocket clients (QUOTE_UPDATE)
```

### 2. Intraday Market Data (Real-Time)
```
Alpaca WebSocket → IntradayIngestionService → Kafka (raw.intraday_*)
  → Validation Consumer → Kafka (validated.intraday_bars)
  → TimescaleDB Writer → market_data.idx_equity_ohlcv_tick
  → Kafka→Redis Bridge → WebSocket clients (TRADE_UPDATE / BAR_UPDATE)
```

### 3. Strategy Signal Pipeline
```
Strategy Engine → generate_signals() → Kafka (strategy.signals.*)
  → Paper Trading Executor → simulated fills → NAV snapshots
  → OR Live Executor → Alpaca order → fill → position update
  → Kafka→Redis Bridge → WebSocket clients (SIGNAL_UPDATE)
```

### 4. Backtesting Pipeline
```
CLI / API → BacktestOrchestrator
  → Load OHLCV from TimescaleDB (or synthetic data)
  → IDXMomentumCrossSectionStrategy.generate_signals_full()
  → run_momentum_backtest() with IDXTransactionCostModel
  → BacktestResult (equity curve, metrics, trade log)
  → Persist to backtest_runs table
```

## Key Components

| Component | Path | Description |
|-----------|------|-------------|
| **API Gateway** | `services/api/` | FastAPI app, REST + WebSocket |
| **HTTP Routers** | `apps/api/http_routers/` | 15+ route modules |
| **WebSocket Gateway** | `services/api/websocket_gateway/` | Kafka→Redis bridge, WS handlers |
| **Strategy Engine** | `strategy_engine/` | 5 strategies + base interface |
| **Backtesting** | `strategy_engine/backtesting/` | Vectorbt engine, cost model, walk-forward |
| **ML Signal** | `services/research/ml_signal/` | LightGBM, LSTM, feature builder |
| **Paper Trading** | `services/paper_trading/` | Simulation engine, session manager |
| **Backtest Service** | `services/backtesting/` | Orchestrator connecting engine to DB |
| **Data Consumers** | `data_platform/consumers/` | Kafka consumers for ingestion |
| **Database Models** | `data_platform/database_models/` | 17 SQLAlchemy ORM models |
| **Alembic Migrations** | `data_platform/alembic_migrations/` | Schema migrations |
| **Shared** | `shared/` | Auth, RBAC, metrics, logging, DB session |
| **Infrastructure** | `infra/` | Docker, Kafka, Prometheus, Grafana |
| **GCP Terraform** | `deploy/gcp/terraform/` | Cloud Run, Secret Manager |

## Database Schema

TimescaleDB with multiple schemas:

| Schema | Tables | Purpose |
|--------|--------|---------|
| `market_data` | `idx_equity_ohlcv_tick`, `idx_equity_instrument`, `idx_equity_financial_statement`, etc. | Market data (hypertables) |
| `trading` | `strategy_order_lifecycle_record`, `strategy_position_current_snapshot`, `strategy_trade_execution_log` | Order execution |
| `public` | `users`, `strategies`, `backtest_runs`, `signals`, `paper_trading_sessions` | Core entities |
| `macro` | `macro_economic_indicator` | Macro data |
| `commodity` | `commodity_company_profile` | Commodity sector data |
| `governance` | Governance flag tables | ESG/governance data |

## IDX-Specific Design

| Feature | Implementation |
|---------|----------------|
| **Lot size** | 100 shares minimum, all orders rounded down |
| **Settlement** | T+2 (trade date + 2 business days) |
| **No short selling** | Long-only strategies (OJK regulation) |
| **Transaction costs** | Buy: 0.15% + levy + VAT; Sell: 0.25% + levy + VAT + 0.1% PPh |
| **Trading hours** | Session 1: 09:00-12:00 WIB, Session 2: 13:30-16:00 WIB |
| **Trading calendar** | IDX holidays (Hari Libur Nasional) 2024-2026 |
| **Currency** | All values in IDR (Indonesian Rupiah) |
| **Liquidity filter** | Minimum average daily value threshold (default 10B IDR) |

## Monitoring

- **Prometheus**: Scrapes API (8000), ingestion (8001), exporters
- **Grafana**: Overview dashboard with 20+ panels
- **Alerting**: 25 rules across 6 groups (latency, DLQ, intraday, paper trading, risk, system)
- **Metrics**: `pyhron_*` prefix — counters, gauges, histograms

## Deployment

| Environment | Stack | Config |
|-------------|-------|--------|
| **Local dev** | Docker Compose | `infra/docker/docker-compose.yaml` |
| **Staging** | Docker Compose overlay | `docker-compose.staging.yml` |
| **Production** | GCP Cloud Run + Terraform | `deploy/gcp/terraform/` |
