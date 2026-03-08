# Pyhron Operations Runbook

## Quick Start

```bash
# Clone and configure
cp .env.example .env
# Edit .env with your API keys

# Start infrastructure
docker compose up -d

# Verify all services
./scripts/healthcheck.sh

# Run migrations
poetry run alembic upgrade head

# Start API server (development)
poetry run uvicorn apps.api.main:app --reload --port 8000
```

---

## Service Health Checks

| Service | Endpoint/Command | Expected |
|---------|-----------------|----------|
| API | GET /health | `{"status": "ok"}` |
| API | GET /ready | `{"status": "ready"}` |
| PostgreSQL | `pg_isready -h localhost -p 5432` | "accepting connections" |
| Redis | `redis-cli ping` | PONG |
| Kafka | `kafka-topics.sh --list --bootstrap-server localhost:9092` | Topic list |
| MLflow | GET http://localhost:5000 | MLflow UI |

---

## Common Operations

### Restart a single service
```bash
docker compose restart <service-name>
```

### View service logs
```bash
docker compose logs -f --tail 100 <service-name>
```

### Run database migrations
```bash
poetry run alembic upgrade head      # Apply all pending
poetry run alembic downgrade -1      # Rollback last migration
poetry run alembic history           # View migration history
```

### Regenerate protobuf bindings
```bash
./scripts/generate_proto.sh
```

### Trigger manual data ingestion
```bash
# EOD prices
poetry run python -c "
import asyncio
from data_platform.ingestion.idx_eod import IDXEODIngester
asyncio.run(IDXEODIngester().ingest_all())
"
```

---

## Incident Response

### Circuit Breaker Triggered
**Symptom:** Risk engine rejecting all orders for a strategy.
**Check:** `redis-cli GET pyhron:risk:circuit_breaker:<strategy_id>`
**Resolution:**
1. Investigate the breach in Kafka topic `pyhron.risk.breaches`
2. Verify positions via reconciliation
3. Clear via API: `POST /v1/trading/circuit-breaker/clear` with audit reason
4. Or manually: `redis-cli DEL pyhron:risk:circuit_breaker:<strategy_id>`

### Kafka Consumer Lag
**Symptom:** Delayed order processing, stale signals rejected.
**Check:** `kafka-consumer-groups.sh --describe --group risk-engine --bootstrap-server localhost:9092`
**Resolution:**
1. Check consumer logs for errors
2. Verify Kafka broker health
3. Scale consumer instances if throughput is insufficient
4. Check for poison messages in DLQ topics

### Database Connection Pool Exhaustion
**Symptom:** `asyncpg.exceptions.TooManyConnectionsError`
**Check:** `SELECT count(*) FROM pg_stat_activity WHERE datname='pyhron';`
**Resolution:**
1. Check `DATABASE_POOL_SIZE` and `DATABASE_MAX_OVERFLOW` in .env
2. Look for leaked sessions (missing `async with get_session()`)
3. Restart API/worker services to reset pool

### Data Quality Alert
**Symptom:** Ingestion logs show `price_change_too_large` or `invalid_ohlc`.
**Check:** Query `market_ticks` for the symbol around the alert timestamp.
**Resolution:**
1. Check EODHD source data for correctness
2. If data is valid (stock split, IPO), update validation thresholds
3. If data is bad, delete affected rows and re-ingest

---

## Monitoring

### Key Metrics (Prometheus)
- `pyhron_risk_checks_total{result}` — Risk check pass/fail rate
- `pyhron_orders_total{status}` — Order lifecycle counts
- `pyhron_ingestion_rows_total{source}` — Ingestion throughput
- `pyhron_api_request_duration_seconds` — API latency histogram

### Alerts
- **Circuit breaker activated** — Immediate notification
- **Consumer lag > 1000** — Warning
- **API p99 > 2s** — Warning
- **Ingestion failure** — Alert after 2 consecutive failures
- **Database connection pool > 80%** — Warning

---

## Backup & Recovery

### Database Backup
```bash
pg_dump -h localhost -U pyhron -d pyhron -Fc > backup_$(date +%Y%m%d).dump
```

### Database Restore
```bash
pg_restore -h localhost -U pyhron -d pyhron -c backup_YYYYMMDD.dump
```

### Kafka Topic Replay
Events can be replayed by resetting consumer group offsets:
```bash
kafka-consumer-groups.sh --reset-offsets --to-earliest \
  --group risk-engine --topic pyhron.signals \
  --bootstrap-server localhost:9092 --execute
```
