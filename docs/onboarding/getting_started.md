# Getting Started with Pyhron

## Prerequisites

- **Python 3.12+** (3.12 recommended)
- **Poetry 1.7+** (dependency management)
- **Docker & Docker Compose** (local infrastructure)
- **Git**

Optional:
- **Alpaca API keys** (for live/paper market data)
- **Terraform 1.6+** (GCP infrastructure provisioning)

## Quick Start

### 1. Clone and Install

```bash
git clone https://github.com/rafli07p/pyhron.git
cd pyhron
poetry install
```

### 2. Configure Environment

```bash
cp .env.staging.example .env
```

Edit `.env` with your configuration:

```bash
# Required
DATABASE_URL=postgresql+asyncpg://pyhron:pyhron_secret@localhost:5432/pyhron
REDIS_URL=redis://localhost:6379/0
KAFKA_BOOTSTRAP_SERVERS=localhost:9092

# API Keys
ALPACA_API_KEY=your_key_here       # alpaca.markets paper trading
ALPACA_API_SECRET=your_secret_here
EODHD_API_TOKEN=your_token_here    # eodhd.com for EOD data

# Auth
JWT_SECRET_KEY=your_jwt_secret_here
APP_SECRET_KEY=your_app_secret_here
```

### 3. Start Infrastructure

```bash
# Core services (PostgreSQL/TimescaleDB, Redis, Kafka, Zookeeper)
docker compose -f infra/docker/docker-compose.yaml up -d

# Create Kafka topics
bash infra/kafka/kafka-topics.sh
```

### 4. Run Database Migrations

```bash
poetry run alembic -c data_platform/alembic_migrations/alembic.ini upgrade head
```

### 5. Start the API Server

```bash
poetry run uvicorn services.api.main:app --reload --port 8000
```

Visit:
- **Swagger UI**: http://localhost:8000/docs
- **Health Check**: http://localhost:8000/health

### 6. Run a Sample Backtest

```bash
# With synthetic data (no DB required)
poetry run python scripts/run_backtest.py

# With specific symbols
poetry run python scripts/run_backtest.py \
  --symbols BBCA BBRI TLKM ASII \
  --start 2023-01-01 --end 2024-12-31

# Save results to JSON
poetry run python scripts/run_backtest.py --output results/momentum.json

# With data from TimescaleDB
poetry run python scripts/run_backtest.py --use-db
```

### 7. Start Paper Trading

```bash
# Live mode (streams from Alpaca WebSocket)
poetry run python scripts/run_paper_trading.py --mode live

# Simulation mode (replays historical data)
poetry run python scripts/run_paper_trading.py --mode simulation \
  --start 2024-01-01 --end 2024-06-30
```

## Development Workflow

### Running Tests

```bash
# All tests
poetry run pytest

# Unit tests only
poetry run pytest tests/unit/ -v

# Integration tests
poetry run pytest tests/integration/ -v

# With coverage
poetry run pytest --cov=. --cov-report=term-missing
```

### Code Quality

```bash
# Lint
poetry run ruff check .

# Auto-fix lint issues
poetry run ruff check --fix .

# Format
poetry run ruff format .

# Type checking
poetry run mypy apps/ shared/ services/ data_platform/ strategy_engine/ \
  --ignore-missing-imports
```

### Staging Deployment

```bash
# Deploy with Docker Compose overlay
bash scripts/deploy_staging.sh

# View logs
bash scripts/deploy_staging.sh --logs

# Tear down
bash scripts/deploy_staging.sh --down
```

## Project Structure

```
pyhron/
├── apps/api/http_routers/     # FastAPI route handlers (15+ modules)
├── services/
│   ├── api/                   # API gateway, WebSocket, middleware
│   ├── broker_connectivity/   # Alpaca adapter
│   ├── paper_trading/         # Paper trading engine
│   ├── backtesting/           # Backtest orchestrator
│   ├── research/ml_signal/    # ML alpha models (LightGBM, LSTM)
│   └── oms/                   # Order management
├── strategy_engine/
│   ├── backtesting/           # Vectorbt engine, cost model, walk-forward
│   ├── live_execution/        # Position sizer, signal publisher
│   ├── idx_momentum_*.py      # 5 strategy implementations
│   └── idx_trading_calendar.py
├── data_platform/
│   ├── database_models/       # 17 SQLAlchemy ORM models
│   ├── consumers/             # Kafka consumers (ingestion, validation, writer)
│   └── alembic_migrations/    # Database migrations
├── shared/                    # Auth, RBAC, metrics, logging, encryption
├── scripts/                   # CLI tools (backtest, paper trading, deploy)
├── infra/                     # Docker, Kafka, Prometheus, Grafana
├── deploy/                    # GCP Terraform, staging config
├── tests/                     # Unit, integration, benchmarks
└── docs/                      # Architecture, API, onboarding, compliance
```

## Key Concepts

### Strategies Available

| Strategy | Module | Description |
|----------|--------|-------------|
| **Momentum 12-1** | `idx_momentum_cross_section_strategy.py` | Jegadeesh-Titman adapted for IDX |
| **Bollinger Mean Reversion** | `idx_bollinger_mean_reversion_strategy.py` | Bollinger Bands + IHSG regime filter |
| **Pairs Cointegration** | `idx_pairs_cointegration_strategy.py` | Engle-Granger with Kalman filter |
| **Value Factor** | `idx_value_factor_strategy.py` | PBV + ROE composite scoring |
| **Sector Rotation** | `idx_sector_rotation_strategy.py` | Momentum-based sector selection |

### Kafka Topics

All events flow through Kafka (30+ topics). Key topics:

| Topic | Purpose |
|-------|---------|
| `pyhron.raw.eod_ohlcv` | Raw EOD data from EODHD |
| `pyhron.validated.eod_ohlcv` | Validated EOD data |
| `pyhron.raw.intraday_trades` | Real-time trades from Alpaca |
| `pyhron.raw.intraday_bars` | Real-time minute bars |
| `pyhron.orders.order_submitted` | Order lifecycle events |
| `pyhron.strategy.signals.*` | Strategy signal events |
| `pyhron.paper.*` | Paper trading events |

### Monitoring

- **Prometheus**: http://localhost:9090 — all `pyhron_*` metrics
- **Grafana**: http://localhost:3000 (admin/pyhron_grafana)
- **Alerting**: 25 rules for latency, DLQ depth, drawdown, system health

## Troubleshooting

**Database connection refused:**
```bash
docker compose -f infra/docker/docker-compose.yaml ps timescaledb
docker compose -f infra/docker/docker-compose.yaml logs timescaledb
```

**Kafka topics not created:**
```bash
bash infra/kafka/kafka-topics.sh
```

**Backtest exits immediately:**
- Without `--use-db`, synthetic data is generated automatically
- With `--use-db`, ensure TimescaleDB has OHLCV data loaded

**Alpaca WebSocket not connecting:**
- Verify `ALPACA_API_KEY` and `ALPACA_API_SECRET` are set
- Paper trading keys from https://app.alpaca.markets/paper/dashboard/overview
