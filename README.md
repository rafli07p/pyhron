# Pyhron

Integrated quantitative trading and research intelligence platform for
Indonesian capital markets (IDX equities) with global market expansion path.

## Architecture

Event-driven microservices communicating via Kafka. All inter-service
contracts defined in Protobuf (`proto/`). Designed for zero-rewrite
migration of execution-critical services (Risk Engine, OMS, Broker
Adapter) to Rust.

```
Strategy → [Kafka: pyhron.signals] → Risk Engine → [Kafka: pyhron.orders.risk-decisions] → OMS → Broker
```

## Services

| Service | Language | Description |
|---|---|---|
| api | Python/FastAPI | Research terminal REST API |
| risk-engine | Python → Rust | Pre-trade risk validation |
| oms | Python → Rust | Order lifecycle management |
| broker | Python → Rust | Exchange connectivity |
| data-platform | Python | Market data ingestion |
| worker | Python/Celery | Scheduled ingestion tasks |

## Prerequisites

- Python 3.12+
- Docker + Docker Compose
- PostgreSQL 16 + TimescaleDB extension
- protobuf compiler (`brew install protobuf` / `apt install protobuf-compiler`)

## Quick Start

```bash
# 1. Clone and enter the repository
git clone https://github.com/rafli07p/pyhron.git && cd pyhron

# 2. Copy environment template
cp .env.example .env

# 3. Generate Protobuf bindings
pip install grpcio-tools
bash scripts/generate_proto.sh

# 4. Start infrastructure
docker compose up -d

# 5. Wait for services to stabilise (~60s), then verify
bash scripts/healthcheck.sh

# 6. Run tests
pytest tests/ -v
```

See `docs/runbook.md` for detailed operational procedures.

## IDX Data Sources

| Source | Coverage | Tier |
|---|---|---|
| EODHD | OHLCV EOD, Fundamentals, Dividends | Primary (paid) |
| yfinance | OHLCV EOD | Fallback (free) |
| IDX.co.id | Disclosure PDFs, Corporate Actions | Scraped |
| RSS Feeds | News (Bisnis, Kontan, CNBC Indonesia) | Free |

## Project Structure

```
pyhron/
├── proto/             Protobuf contracts (language-agnostic seams)
├── shared/            Shared libraries (config, database, messaging)
├── services/          Microservices (risk-engine, oms, broker)
├── data-platform/     Market data ingestion + storage
├── apps/              User-facing applications (API, terminal)
├── strategies/        Trading strategy implementations
├── infra/             Docker, Kubernetes, Terraform
├── scripts/           Operational scripts
├── tests/             Unit, integration, e2e tests
└── docs/              ADRs, data dictionary, runbook
```

## License

MIT
