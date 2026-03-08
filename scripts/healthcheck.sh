#!/usr/bin/env bash
# =============================================================================
# Pyhron Platform — Local Health Check
# =============================================================================
# Verifies all services are up and responding after `docker compose up`.
# Exit 0 = all healthy, Exit 1 = one or more checks failed.
#
# Usage:
#   ./scripts/healthcheck.sh
#   ./scripts/healthcheck.sh --verbose
# =============================================================================

set -euo pipefail

VERBOSE="${1:-}"
PASS=0
FAIL=0
COMPOSE_FILE="infra/docker/docker-compose.yaml"

if [ -t 1 ]; then
    GREEN='\033[0;32m'
    RED='\033[0;31m'
    NC='\033[0m'
else
    GREEN='' RED='' NC=''
fi

check() {
    local name="$1"
    local cmd="$2"
    local result

    if result=$(eval "$cmd" 2>&1); then
        printf "  ${GREEN}✓${NC} %-30s %s\n" "$name" "OK"
        [ "$VERBOSE" = "--verbose" ] && echo "    $result"
        PASS=$((PASS + 1))
    else
        printf "  ${RED}✗${NC} %-30s %s\n" "$name" "FAILED"
        [ "$VERBOSE" = "--verbose" ] && echo "    $result"
        FAIL=$((FAIL + 1))
    fi
}

echo ""
echo "Pyhron Platform — Health Check"
echo "=============================="
echo ""

# ── API Service ──────────────────────────────────────────────────────────────
echo "API Service:"
check "GET /health" \
    "curl -sf http://localhost:${APP_PORT:-8000}/health"
check "GET /docs (OpenAPI)" \
    "curl -sf -o /dev/null -w '%{http_code}' http://localhost:${APP_PORT:-8000}/docs | grep -q 200"

# ── PostgreSQL (TimescaleDB) ─────────────────────────────────────────────────
echo ""
echo "PostgreSQL (TimescaleDB):"
check "pg_isready" \
    "docker compose -f $COMPOSE_FILE exec -T postgres pg_isready -U ${POSTGRES_USER:-pyhron} -d ${POSTGRES_DB:-pyhron}"
check "TimescaleDB extension" \
    "docker compose -f $COMPOSE_FILE exec -T postgres psql -U ${POSTGRES_USER:-pyhron} -d ${POSTGRES_DB:-pyhron} -tAc \"SELECT extname FROM pg_extension WHERE extname='timescaledb';\" | grep -q timescaledb"

# ── Redis ────────────────────────────────────────────────────────────────────
echo ""
echo "Redis:"
check "PING" \
    "docker compose -f $COMPOSE_FILE exec -T redis redis-cli ping | grep -q PONG"

# ── Kafka ────────────────────────────────────────────────────────────────────
echo ""
echo "Kafka:"
check "Broker API versions" \
    "docker compose -f $COMPOSE_FILE exec -T kafka kafka-broker-api-versions --bootstrap-server localhost:9092 | head -1 | grep -q 'ApiVersion'"
check "Topic list" \
    "docker compose -f $COMPOSE_FILE exec -T kafka kafka-topics --bootstrap-server localhost:29092 --list 2>&1"

# ── MLflow ───────────────────────────────────────────────────────────────────
echo ""
echo "MLflow:"
check "GET /health" \
    "curl -sf http://localhost:${MLFLOW_PORT:-5000}/health"

# ── Summary ──────────────────────────────────────────────────────────────────
echo ""
echo "----------------------------------------------"
TOTAL=$((PASS + FAIL))
printf "Results: ${GREEN}%d passed${NC}, ${RED}%d failed${NC} (out of %d)\n" "$PASS" "$FAIL" "$TOTAL"
echo "----------------------------------------------"

if [ "$FAIL" -gt 0 ]; then
    printf "${RED}Some checks failed. Run with --verbose for details.${NC}\n"
    exit 1
fi

printf "${GREEN}All services healthy.${NC}\n"
exit 0
