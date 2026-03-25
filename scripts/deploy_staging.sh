#!/usr/bin/env bash
# =============================================================================
# Pyhron — Staging Deployment Script
# =============================================================================
# Deploys the full Pyhron stack to a staging environment using Docker Compose.
#
# Prerequisites:
#   - Docker and Docker Compose v2 installed
#   - .env.staging file created from .env.staging.example
#   - Alpaca paper trading API keys configured
#
# Usage:
#   ./scripts/deploy_staging.sh          # Deploy all services
#   ./scripts/deploy_staging.sh --down   # Tear down staging
#   ./scripts/deploy_staging.sh --logs   # Follow logs
#   ./scripts/deploy_staging.sh --status # Show service status
# =============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$PROJECT_ROOT"

ENV_FILE=".env.staging"
COMPOSE_FILES="-f infra/docker/docker-compose.yaml -f docker-compose.staging.yml"
COMPOSE_CMD="docker compose --env-file $ENV_FILE $COMPOSE_FILES"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

log_info() { echo -e "${GREEN}[INFO]${NC} $*"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $*"; }
log_error() { echo -e "${RED}[ERROR]${NC} $*"; }

# ── Pre-flight checks ────────────────────────────────────────────────────────
preflight() {
    if ! command -v docker &>/dev/null; then
        log_error "Docker is not installed"
        exit 1
    fi

    if ! docker compose version &>/dev/null; then
        log_error "Docker Compose v2 is required"
        exit 1
    fi

    if [ ! -f "$ENV_FILE" ]; then
        log_error "$ENV_FILE not found. Create it from .env.staging.example:"
        echo "  cp .env.staging.example .env.staging"
        exit 1
    fi

    # Validate required secrets are set
    local required_vars=("POSTGRES_PASSWORD" "REDIS_PASSWORD" "APP_SECRET_KEY" "JWT_SECRET_KEY" "GRAFANA_ADMIN_PASSWORD")
    for var in "${required_vars[@]}"; do
        val=$(grep "^${var}=" "$ENV_FILE" | cut -d= -f2-)
        if [ -z "$val" ] || [[ "$val" == REPLACE* ]]; then
            log_error "$var is not set in $ENV_FILE"
            exit 1
        fi
    done

    log_info "Pre-flight checks passed"
}

# ── Deploy ────────────────────────────────────────────────────────────────────
deploy() {
    preflight

    log_info "Building Docker images..."
    $COMPOSE_CMD build --parallel

    log_info "Running database migrations..."
    $COMPOSE_CMD up -d postgres
    sleep 5  # Wait for PostgreSQL to be ready

    $COMPOSE_CMD run --rm api \
        alembic -c data_platform/alembic_migrations/alembic.ini upgrade head

    log_info "Starting all services..."
    $COMPOSE_CMD up -d

    log_info "Waiting for services to become healthy..."
    sleep 10

    $COMPOSE_CMD ps

    echo ""
    log_info "Staging deployment complete!"
    echo ""
    echo "  API:        http://localhost:${APP_PORT:-8000}/health"
    echo "  API Docs:   http://localhost:${APP_PORT:-8000}/docs"
    echo "  Prometheus: http://localhost:${PROMETHEUS_PORT:-9090}"
    echo "  Grafana:    http://localhost:${GRAFANA_PORT:-3000}"
    echo ""
    echo "  View logs:  $0 --logs"
    echo "  Tear down:  $0 --down"
}

# ── Tear down ─────────────────────────────────────────────────────────────────
teardown() {
    log_warn "Tearing down staging environment..."
    $COMPOSE_CMD down
    log_info "Staging environment stopped (volumes preserved)"
    echo "  To remove volumes: $COMPOSE_CMD down -v"
}

# ── Logs ──────────────────────────────────────────────────────────────────────
follow_logs() {
    $COMPOSE_CMD logs -f --tail=100
}

# ── Status ────────────────────────────────────────────────────────────────────
show_status() {
    $COMPOSE_CMD ps
    echo ""
    log_info "Health check:"
    curl -sf http://localhost:${APP_PORT:-8000}/health 2>/dev/null && echo " API: OK" || echo " API: UNREACHABLE"
}

# ── Main ──────────────────────────────────────────────────────────────────────
case "${1:-deploy}" in
    --down|down)     teardown ;;
    --logs|logs)     follow_logs ;;
    --status|status) show_status ;;
    deploy|*)        deploy ;;
esac
