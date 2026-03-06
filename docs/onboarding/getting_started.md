# Getting Started with Enthropy

## Prerequisites

- Python 3.10+
- Poetry
- Docker & Docker Compose
- PostgreSQL 15+ (or use Docker)
- Redis 7+ (or use Docker)

## Quick Start

### 1. Clone and Install

```bash
git clone <repository-url>
cd enthropy
poetry install
```

### 2. Configure Environment

```bash
cp .env.example .env
# Edit .env with your API keys
```

**Required API Keys:**
- `MASSIVE_API_KEY`: Get from [Massive](https://massive.com) (formerly Polygon.io)
- `ALPACA_API_KEY` + `ALPACA_SECRET_KEY`: Get from [Alpaca](https://alpaca.markets)
- yfinance requires no API key

### 3. Start Infrastructure

```bash
docker-compose -f infra/docker/docker-compose.yaml up -d
```

### 4. Setup Database

```bash
poetry run python scripts/setup_db.py
```

### 5. Seed Development Data

```bash
poetry run python scripts/seed_data.py
```

### 6. Run the API Server

```bash
poetry run uvicorn services.api.rest_gateway:app --reload --port 8000
```

Visit http://localhost:8000/docs for the interactive API documentation.

## Development Workflow

### Branching Strategy
- **Trunk-based development** with short-lived feature branches
- Branch naming: `feature/<ticket>-<description>`, `fix/<ticket>-<description>`
- All PRs require review and passing CI

### Feature Flags
- Use `shared/configs` settings to toggle features
- New features should be behind flags until stable

### Running Tests

```bash
# Unit tests
poetry run pytest tests/unit/ -v

# Integration tests (requires running services)
poetry run pytest tests/integration/ -v

# E2E tests (requires API keys)
poetry run pytest tests/e2e/ -v

# Load tests
poetry run locust -f tests/benchmarks/locustfile.py --host http://localhost:8000
```

### Code Quality

```bash
# Lint
poetry run ruff check .

# Format
poetry run ruff format .
```

## Project Structure

- `apps/` - Frontend application layers (terminal, research, admin)
- `services/` - Core business logic (market data, execution, portfolio, risk, research)
- `data-platform/` - Data storage and management
- `strategies/` - Trading strategy framework
- `shared/` - Common schemas, utilities, security
- `infra/` - Infrastructure configs (Docker, K8s, Terraform)
- `tests/` - Test suites
- `docs/` - Documentation
