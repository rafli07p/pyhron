# Enthropy

**Bloomberg-style algorithmic quant research terminal.**

Enthropy is an integrated platform for quantitative research, algorithmic trading strategy development, and real-time market analysis. It unifies market data ingestion, ML-driven signal generation, backtesting, and live execution into a single coherent system.

---

## Features

- **Multi-source market data** -- Real-time and historical data from Polygon, Alpaca, Yahoo Finance, and 100+ crypto exchanges via CCXT.
- **Quantitative analytics** -- QuantLib-powered pricing, Greeks, yield curves, and risk models.
- **ML pipeline** -- PyTorch and scikit-learn model training with MLflow experiment tracking.
- **Strategy framework** -- Modular strategy authoring with built-in backtesting and walk-forward optimization.
- **Live execution** -- Paper and live trading through Alpaca with order management and position tracking.
- **Event streaming** -- Kafka-based event bus for real-time signal propagation and system decoupling.
- **REST & WebSocket API** -- FastAPI-powered endpoints with rate limiting, JWT auth, and WebSocket feeds.
- **Distributed compute** -- Dask cluster support for large-scale backtests and data processing.
- **Resilience** -- Circuit breakers, retry policies, structured logging, and health monitoring.

## Tech Stack

| Layer | Technologies |
|---|---|
| **Data** | Polygon, Alpaca, yfinance, CCXT, Kafka, Redis |
| **Compute** | Pandas, NumPy, SciPy, Dask, Celery |
| **ML** | PyTorch, scikit-learn, MLflow |
| **Quant** | QuantLib |
| **API** | FastAPI, Uvicorn, Pydantic, WebSockets |
| **Storage** | PostgreSQL (SQLAlchemy + Alembic), Redis |
| **Auth** | JWT (PyJWT), passlib, cryptography |
| **Infra** | Docker, GitHub Actions, pre-commit, Ruff |

## Architecture Overview

```
                         +------------------+
                         |   FastAPI Gateway |
                         |  (REST + WS)     |
                         +--------+---------+
                                  |
              +-------------------+-------------------+
              |                   |                   |
     +--------v-------+  +-------v--------+  +-------v--------+
     | Market Data Svc|  | Strategy Engine |  |  ML Pipeline   |
     | (Polygon/Alpaca|  | (Backtest/Live) |  | (Train/Predict)|
     | /yfinance/CCXT)|  +-------+--------+  +-------+--------+
     +--------+-------+          |                    |
              |                  |                    |
              +--------+---------+--------------------+
                       |                    |
              +--------v-------+   +--------v-------+
              |  Kafka Event   |   |   PostgreSQL   |
              |     Bus        |   |   + Redis      |
              +----------------+   +----------------+
```

- **apps/** -- User-facing applications and dashboards.
- **services/** -- Core microservices (data ingestion, execution, analytics).
- **shared/** -- Common libraries, models, and utilities.
- **strategies/** -- Trading strategy implementations.
- **data-platform/** -- Data pipeline and storage layer.
- **infra/** -- Docker, Kubernetes, and deployment configs.
- **scripts/** -- Operational and maintenance scripts.
- **tests/** -- Unit, integration, and load tests.

## Setup

### Prerequisites

- Python 3.10+
- [Poetry](https://python-poetry.org/docs/#installation)
- Docker & Docker Compose
- PostgreSQL 15+
- Redis 7+

### Installation

```bash
# Clone the repository
git clone https://github.com/your-org/enthropy.git
cd enthropy

# Install dependencies
poetry install

# Copy environment template and fill in your keys
cp .env.example .env

# Start infrastructure services
docker compose up -d postgres redis kafka

# Run database migrations
poetry run alembic upgrade head

# Start the development server
poetry run uvicorn apps.api.main:app --reload --host 0.0.0.0 --port 8000
```

### Docker

```bash
# Build and run the full stack
docker compose up --build

# Run in detached mode
docker compose up -d --build
```

## API Key Configuration

Enthropy integrates with multiple data and brokerage providers. Set the following in your `.env` file:

### Polygon.io

Real-time and historical US market data (equities, options, forex, crypto).

1. Sign up at [polygon.io](https://polygon.io/).
2. Navigate to your dashboard and copy your API key.
3. Set `MASSIVE_API_KEY` in `.env`.

### Alpaca

Commission-free trading and market data API for US equities.

1. Create an account at [alpaca.markets](https://alpaca.markets/).
2. Generate API keys from the dashboard (paper or live).
3. Set `ALPACA_API_KEY`, `ALPACA_SECRET_KEY`, and `ALPACA_BASE_URL` in `.env`.
4. Use `https://paper-api.alpaca.markets` for paper trading.

### Yahoo Finance

Historical market data (no API key required). Data is accessed via the `yfinance` library with no authentication. Rate limits apply.

### CCXT (Crypto Exchanges)

Unified API for 100+ cryptocurrency exchanges.

1. Create an account on your chosen exchange (Binance, Coinbase, Kraken, etc.).
2. Generate API keys with appropriate permissions (read-only recommended for research).
3. Set `CCXT_EXCHANGE` to your exchange ID (e.g., `binance`).
4. Pass exchange-specific credentials through environment variables or the config system.

## Development

```bash
# Run linter
poetry run ruff check .

# Run formatter
poetry run ruff format .

# Run tests
poetry run pytest

# Run tests with coverage
poetry run pytest --cov

# Run load tests
poetry run locust -f tests/load/locustfile.py
```

## License

MIT License. See [LICENSE](LICENSE) for details.
