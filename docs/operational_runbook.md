# Pyhron Operational Runbook

Standard operating procedures for common platform operations. All commands assume access to the deployment environment with appropriate credentials.

---

## 1. Deployment

### Standard Deployment (main branch)

```bash
# 1. Ensure CI passes on main
gh run list --branch main --limit 5

# 2. Build Docker images
docker build -f infra/docker/api.Dockerfile -t pyhron-api:$(git rev-parse --short HEAD) .
docker build -f infra/docker/worker.Dockerfile -t pyhron-worker:$(git rev-parse --short HEAD) .

# 3. Push to container registry
docker tag pyhron-api:$(git rev-parse --short HEAD) registry.example.com/pyhron-api:$(git rev-parse --short HEAD)
docker push registry.example.com/pyhron-api:$(git rev-parse --short HEAD)
docker tag pyhron-worker:$(git rev-parse --short HEAD) registry.example.com/pyhron-worker:$(git rev-parse --short HEAD)
docker push registry.example.com/pyhron-worker:$(git rev-parse --short HEAD)

# 4. Apply database migrations BEFORE deploying new code
poetry run alembic upgrade head

# 5. Update Kubernetes deployments
kubectl set image deployment/pyhron-api api=registry.example.com/pyhron-api:$(git rev-parse --short HEAD) -n pyhron
kubectl set image deployment/pyhron-worker worker=registry.example.com/pyhron-worker:$(git rev-parse --short HEAD) -n pyhron

# 6. Verify rollout
kubectl rollout status deployment/pyhron-api -n pyhron --timeout=120s
kubectl rollout status deployment/pyhron-worker -n pyhron --timeout=120s

# 7. Smoke test
curl -s https://api.pyhron.example.com/health | jq .
curl -s https://api.pyhron.example.com/ready | jq .
```

### Local Development Deployment

```bash
docker compose up -d
poetry install --with dev,test
poetry run alembic upgrade head
poetry run uvicorn apps.api.main:app --reload --port 8000
```

---

## 2. Rollback

### Application Rollback (Kubernetes)

```bash
# 1. Check rollout history
kubectl rollout history deployment/pyhron-api -n pyhron

# 2. Rollback to previous revision
kubectl rollout undo deployment/pyhron-api -n pyhron
kubectl rollout undo deployment/pyhron-worker -n pyhron

# 3. Verify rollback completed
kubectl rollout status deployment/pyhron-api -n pyhron --timeout=120s

# 4. Confirm running version
kubectl get pods -n pyhron -o jsonpath='{.items[*].spec.containers[*].image}'
```

### Database Migration Rollback

```bash
# Rollback last migration
poetry run alembic downgrade -1

# Rollback to a specific revision
poetry run alembic downgrade <revision_id>

# View migration history to find the target revision
poetry run alembic history --verbose
```

**Important:** Always rollback migrations BEFORE rolling back application code if the migration introduced breaking schema changes.

---

## 3. Database Migration

### Apply Migrations

```bash
# Check current revision
poetry run alembic current

# View pending migrations
poetry run alembic history --verbose

# Apply all pending migrations
poetry run alembic upgrade head

# Apply one migration at a time (safer for production)
poetry run alembic upgrade +1
```

### Create a New Migration

```bash
# Auto-generate from model changes
poetry run alembic revision --autogenerate -m "add_column_xyz_to_orders"

# Create empty migration for manual SQL
poetry run alembic revision -m "create_custom_index"
```

### Production Migration Checklist

1. Review the generated migration SQL: `poetry run alembic upgrade head --sql`
2. Test migration on a staging database with production data volume.
3. Ensure migration is backward-compatible (old code can run with new schema).
4. Take a database backup before applying: `pg_dump -h $DB_HOST -U pyhron -d pyhron -Fc > backup_pre_migration_$(date +%Y%m%d_%H%M).dump`
5. Apply migration during low-traffic period (before IDX market open, before 08:45 WIB).
6. Verify with: `poetry run alembic current`

---

## 4. Kafka Consumer Lag

### Check Consumer Lag

```bash
# List all consumer groups
kafka-consumer-groups.sh --list --bootstrap-server $KAFKA_BOOTSTRAP_SERVERS

# Describe a specific consumer group
kafka-consumer-groups.sh --describe --group risk-engine \
  --bootstrap-server $KAFKA_BOOTSTRAP_SERVERS

# Check all consumer groups at once
for group in risk-engine order-router order-persister position-updater \
  market-data-persister macro-persister commodity-persister; do
  echo "=== $group ==="
  kafka-consumer-groups.sh --describe --group "$group" \
    --bootstrap-server $KAFKA_BOOTSTRAP_SERVERS 2>/dev/null | tail -5
done
```

### Resolve High Consumer Lag

**Symptom:** LAG column shows values >1000 or growing continuously.

1. **Check consumer health:**
   ```bash
   # Verify consumer pods are running
   kubectl get pods -n pyhron -l app=risk-engine
   kubectl logs -n pyhron -l app=risk-engine --tail=50
   ```

2. **Check for poison messages (processing failures):**
   ```bash
   # Check DLQ for the affected topic
   kafka-console-consumer.sh --topic pyhron.dlq.equity-strategy-signals \
     --bootstrap-server $KAFKA_BOOTSTRAP_SERVERS --from-beginning --max-messages 5
   ```

3. **Scale consumers (if throughput is the bottleneck):**
   ```bash
   kubectl scale deployment/risk-engine --replicas=3 -n pyhron
   ```

4. **Reset offsets (last resort, causes reprocessing):**
   ```bash
   # Stop consumers first
   kubectl scale deployment/risk-engine --replicas=0 -n pyhron

   # Reset to latest (skip unprocessed messages)
   kafka-consumer-groups.sh --reset-offsets --to-latest \
     --group risk-engine --topic pyhron.equity.strategy-signals \
     --bootstrap-server $KAFKA_BOOTSTRAP_SERVERS --execute

   # Restart consumers
   kubectl scale deployment/risk-engine --replicas=2 -n pyhron
   ```

---

## 5. Circuit Breaker Clear

### Check Circuit Breaker State

```bash
# Check if any strategy is halted
redis-cli -h $REDIS_HOST KEYS "pyhron:risk:circuit_breaker:*"

# Check specific strategy
redis-cli -h $REDIS_HOST GET "pyhron:risk:circuit_breaker:momentum_strategy_01"
```

### Clear Circuit Breaker

**Via API (preferred -- creates audit trail):**
```bash
curl -X POST https://api.pyhron.example.com/v1/trading/circuit-breaker/clear \
  -H "Authorization: Bearer $API_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "strategy_id": "momentum_strategy_01",
    "reason": "Manual clear after investigating breach. Position reconciled. Ticket: OPS-1234"
  }'
```

**Via Redis (emergency only):**
```bash
# Clear specific strategy
redis-cli -h $REDIS_HOST DEL "pyhron:risk:circuit_breaker:momentum_strategy_01"

# Clear all circuit breakers (DANGER)
redis-cli -h $REDIS_HOST KEYS "pyhron:risk:circuit_breaker:*" | xargs redis-cli -h $REDIS_HOST DEL
```

### Post-Clear Verification

```bash
# 1. Verify circuit breaker is cleared
redis-cli -h $REDIS_HOST GET "pyhron:risk:circuit_breaker:momentum_strategy_01"
# Should return (nil)

# 2. Check that the strategy is generating signals again
kafka-console-consumer.sh --topic pyhron.equity.strategy-signals \
  --bootstrap-server $KAFKA_BOOTSTRAP_SERVERS --timeout-ms 30000

# 3. Review recent risk breach log
psql -h $DB_HOST -U pyhron -d pyhron -c "
  SELECT breach_time, limit_type, actual_value, limit_value, action_taken
  FROM risk.risk_breach_log
  WHERE strategy_id = 'momentum_strategy_01'
  ORDER BY breach_time DESC LIMIT 10;
"
```

---

## 6. Data Backfill

### Backfill Market Data (EODHD)

```bash
# Backfill specific symbols for a date range
python scripts/run_full_data_backfill.py \
  --source eodhd \
  --symbols BBCA BBRI BMRI TLKM ASII \
  --start-date 2020-01-01 \
  --end-date 2024-12-31

# Backfill all tracked instruments
python scripts/run_full_data_backfill.py --source eodhd --all-instruments
```

### Backfill Macro Indicators

```bash
# Backfill all macro indicators
python scripts/run_full_data_backfill.py --source macro --all-indicators

# Backfill specific indicator
python scripts/run_full_data_backfill.py --source macro --indicator-codes BI_RATE JISDOR CPI_YOY
```

### Backfill Commodity Prices

```bash
python scripts/run_full_data_backfill.py --source commodity --all-commodities
```

### Verification After Backfill

```bash
# Check row counts per source
psql -h $DB_HOST -U pyhron -d pyhron -c "
  SELECT source, COUNT(*), MIN(time)::date AS earliest, MAX(time)::date AS latest
  FROM market_data.market_ticks
  GROUP BY source ORDER BY source;
"

# Check for gaps in daily data
psql -h $DB_HOST -U pyhron -d pyhron -c "
  SELECT symbol, COUNT(*) AS bars,
         MIN(time)::date AS first_bar,
         MAX(time)::date AS last_bar
  FROM market_data.market_ticks
  WHERE symbol IN ('BBCA', 'BBRI', 'TLKM')
  GROUP BY symbol ORDER BY symbol;
"

# Verify data freshness
python scripts/verify_data_pipeline_health.py
```

---

## Service Health Check Quick Reference

| Service | Check Command | Expected |
|---------|--------------|----------|
| API | `curl -s localhost:8000/health` | `{"status": "ok"}` |
| API Readiness | `curl -s localhost:8000/ready` | `{"status": "ready"}` |
| PostgreSQL | `pg_isready -h localhost -p 5432` | "accepting connections" |
| Redis | `redis-cli ping` | `PONG` |
| Kafka | `kafka-topics.sh --list --bootstrap-server localhost:9092` | Topic list |
| MLflow | `curl -s localhost:5000/health` | HTTP 200 |

---

## Monitoring Dashboards

| Dashboard | URL | Key Metrics |
|-----------|-----|-------------|
| System Overview | Grafana `/d/pyhron-overview` | Service health, resource usage |
| Trading Activity | Grafana `/d/pyhron-trading` | Orders, fills, PnL |
| Data Ingestion | Grafana `/d/pyhron-ingestion` | Freshness, row counts, errors |
| Kafka | Grafana `/d/pyhron-kafka` | Consumer lag, throughput, partition balance |
| Risk | Grafana `/d/pyhron-risk` | Breaches, circuit breakers, VaR |

---

## Emergency Contacts

| Role | Responsibility |
|------|---------------|
| On-call Engineer | First responder for all alerts |
| Data Engineer | Data pipeline failures, backfill issues |
| Quant / Strategy Lead | Risk breach investigation, strategy parameter tuning |
| Infrastructure Lead | Kubernetes, database, Kafka cluster issues |
