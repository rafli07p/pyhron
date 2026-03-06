# Getting Started with Enthropy

## Prerequisites

- **Python 3.11+** (3.11 recommended for performance)
- **Poetry 1.7+** (dependency management)
- **Docker & Docker Compose** (local infrastructure)
- **Git** (version control)

Optional but recommended:
- **kubectl** (Kubernetes CLI, for staging/production)
- **Terraform 1.6+** (infrastructure provisioning)
- **Trivy** (container security scanning)

## Quick Start

### 1. Clone and Install

```bash
git clone <repository-url>
cd enthropy
poetry install
```

This installs all dependencies including development tools (pytest, ruff, mypy, locust).

### 2. Configure Environment

```bash
cp .env.example .env
```

Edit `.env` with your configuration:

```bash
# Required
DATABASE_URL=postgresql+asyncpg://enthropy:enthropy_secret@localhost:5432/enthropy
REDIS_URL=redis://localhost:6379/0
KAFKA_BOOTSTRAP_SERVERS=localhost:9092

# API Keys (get from providers)
MARKET_DATA_API_KEY=your_key_here    # Massive/Polygon for US market data
ALPACA_API_KEY=your_key_here         # Alpaca for US order execution
ALPACA_SECRET_KEY=your_secret_here

# Encryption (generate a 256-bit key)
ENCRYPTION_KEY=$(python -c "import base64,os; print(base64.b64encode(os.urandom(32)).decode())")

# Optional
MLFLOW_TRACKING_URI=http://localhost:5000
ENVIRONMENT=development
LOG_LEVEL=DEBUG
```

**API Key Sources:**
- **Massive/Polygon**: [polygon.io](https://polygon.io) - US equity market data
- **Alpaca**: [alpaca.markets](https://alpaca.markets) - Paper/live trading (US)
- **yfinance**: No API key required - Used for IDX (.JK) and fallback data

### 3. Start Infrastructure

```bash
# Core services only
docker compose -f infra/docker/docker-compose.yaml up -d

# Include monitoring stack (Prometheus + Grafana)
docker compose -f infra/docker/docker-compose.yaml --profile monitoring up -d
```

Verify services are running:
```bash
docker compose -f infra/docker/docker-compose.yaml ps
```

### 4. Setup Database

```bash
# Create schemas, tables, indices, and triggers
poetry run python scripts/setup_db.py

# Verify setup
poetry run python scripts/setup_db.py --verify
```

### 5. Seed Development Data

```bash
# Download 2 years of IDX blue chip data
poetry run python scripts/seed_data.py

# Or specific symbols
poetry run python scripts/seed_data.py --symbols BBCA.JK TLKM.JK --period 5y
```

### 6. Run the API Server

```bash
poetry run uvicorn enthropy.api.main:app --reload --port 8000
```

Visit:
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc
- **Health Check**: http://localhost:8000/health
- **Grafana** (if monitoring enabled): http://localhost:3000 (admin/enthropy_grafana)
- **Prometheus**: http://localhost:9090

### 7. Run a Sample Backtest

```bash
poetry run python scripts/run_backtest.py \
  --strategy momentum \
  --symbols BBCA.JK TLKM.JK BMRI.JK \
  --start 2023-01-01 \
  --end 2023-12-31 \
  --output results/my_first_backtest.json
```

## Development Workflow

### Branching Strategy (Trunk-Based Development)

We follow trunk-based development with short-lived feature branches:

```
main (trunk)
  ├── feature/ENT-123-add-momentum-signal    # Feature branch (< 2 days)
  ├── fix/ENT-456-fix-order-fill-price       # Bug fix branch
  └── chore/ENT-789-upgrade-pydantic         # Maintenance branch
```

**Rules:**
- Branch from `main`, merge back to `main`
- Keep branches short-lived (ideally < 2 days)
- All PRs require at least 1 review and passing CI
- Squash merge to keep history clean
- No long-lived feature branches

### Feature Flags

New features should be behind flags until stable:

```python
from enthropy.shared.configs import settings

if settings.feature_flags.get("enable_new_risk_model", False):
    result = new_risk_model.calculate(portfolio)
else:
    result = legacy_risk_model.calculate(portfolio)
```

Feature flags are controlled via:
- Environment variables: `FEATURE_FLAG_ENABLE_NEW_RISK_MODEL=true`
- Config file: `configs/feature_flags.yaml`
- Admin API: `PUT /admin/feature-flags/{flag_name}`

### Running Tests

```bash
# Unit tests (fast, no external deps)
poetry run pytest tests/unit/ -v

# Unit tests with coverage
poetry run pytest tests/unit/ --cov=src/ --cov-report=term-missing

# Integration tests (requires Docker services running)
poetry run pytest tests/integration/ -v

# E2E tests (requires API keys)
poetry run pytest tests/e2e/ -v

# Run specific test file
poetry run pytest tests/unit/test_risk_limits.py -v

# Run tests matching a pattern
poetry run pytest -k "test_var" -v

# Load testing (starts Locust web UI at http://localhost:8089)
poetry run locust -f tests/benchmarks/locustfile.py --host http://localhost:8000

# Headless load test
poetry run locust -f tests/benchmarks/locustfile.py \
  --host http://localhost:8000 \
  --users 1000 --spawn-rate 50 --run-time 5m --headless
```

### Code Quality

```bash
# Lint (check)
poetry run ruff check src/ tests/

# Lint (fix automatically)
poetry run ruff check --fix src/ tests/

# Format (check)
poetry run ruff format --check src/ tests/

# Format (apply)
poetry run ruff format src/ tests/

# Type checking
poetry run mypy src/ --ignore-missing-imports
```

### Building & Deploying

```bash
# Build Docker image
docker build -t enthropy-api:latest -f infra/docker/Dockerfile .

# Security scan
trivy image enthropy-api:latest --severity HIGH,CRITICAL

# Deploy (with confirmation for production)
./infra/deployment/deploy.sh staging latest
./infra/deployment/deploy.sh production v1.2.3

# Rollback
./infra/deployment/deploy.sh --rollback production
```

## Project Structure

```
enthropy/
├── src/enthropy/           # Source code
│   ├── api/                # FastAPI application
│   ├── market_data/        # Market data ingestion & caching
│   ├── execution/          # Order routing & exchange connectors
│   ├── strategy/           # Trading strategies
│   ├── risk/               # Risk engine & limits
│   ├── pnl/                # P&L calculation engine
│   ├── backtest/           # Backtesting engine
│   ├── compliance/         # Regulatory reporting
│   └── shared/             # Shared schemas, encryption, utils
├── tests/                  # Test suites
│   ├── unit/               # Fast, isolated unit tests
│   ├── integration/        # Tests requiring external services
│   ├── e2e/                # End-to-end pipeline tests
│   ├── benchmarks/         # Load & performance tests (Locust)
│   └── conftest.py         # Shared fixtures
├── scripts/                # CLI utilities
│   ├── setup_db.py         # Database initialization
│   ├── seed_data.py        # Historical data seeding
│   └── run_backtest.py     # Backtest runner
├── infra/                  # Infrastructure
│   ├── docker/             # Docker Compose & Dockerfile
│   ├── kubernetes/         # K8s manifests
│   ├── terraform/          # AWS infrastructure (IaC)
│   ├── monitoring/         # Prometheus, Grafana, alerts
│   ├── deployment/         # Deployment scripts
│   ├── ci-cd/              # CI/CD pipeline
│   └── build/              # Bazel build config
├── docs/                   # Documentation
│   ├── api/                # API docs & Sphinx config
│   ├── architecture/       # Architecture decisions
│   ├── compliance/         # UU PDP & SEC/OJK guides
│   └── onboarding/         # This guide
├── pyproject.toml          # Poetry config & tool settings
└── alembic.ini             # Database migration config
```

## Key Contacts

- **Platform Engineering**: Responsible for infra, CI/CD, monitoring
- **Trading Systems**: Order execution, market data, risk engine
- **Research**: Backtesting, strategy development, ML experiments
- **Compliance**: Regulatory reporting, data privacy

## Troubleshooting

### Common Issues

**Database connection refused:**
```bash
# Check if PostgreSQL is running
docker compose -f infra/docker/docker-compose.yaml ps postgres
# Check logs
docker compose -f infra/docker/docker-compose.yaml logs postgres
```

**Redis connection error:**
```bash
docker compose -f infra/docker/docker-compose.yaml ps redis
docker compose -f infra/docker/docker-compose.yaml logs redis
```

**Tests failing with import errors:**
```bash
# Ensure you're using the Poetry virtual environment
poetry shell
# Or prefix commands with `poetry run`
poetry run pytest tests/unit/ -v
```

**Market data API key not working:**
- Verify the key is set in `.env`
- Integration tests will be skipped if `MARKET_DATA_API_KEY` is not set
- yfinance (no key required) is used as fallback for IDX data

## Next Steps

1. Read the [Architecture Overview](../architecture/overview.md) to understand the system design
2. Review the [API Documentation](../api/openapi.md) for endpoint details
3. Check [UU PDP Guide](../compliance/uu_pdp_guide.md) for data privacy requirements
4. Explore tests in `tests/unit/` to understand component behavior
5. Run a backtest with `scripts/run_backtest.py` to see the full pipeline in action
