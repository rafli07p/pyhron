# Pyhron Production Runbook

## Deployment Checklist (Pre-deploy)

- [ ] All CI jobs green on main
- [ ] Migration dry-run verified: `alembic upgrade head --sql | head -100`
- [ ] Secrets in Secret Manager updated if rotated
- [ ] Staging smoke test passed
- [ ] Rollback image SHA documented

## Deployment Procedure

1. Create git tag: `git tag v1.x.x && git push origin v1.x.x`
2. CI runs build -> push -> staging -> production automatically
3. Monitor Cloud Run metrics during rollout (5 min window)
4. Verify /health endpoint returns 200
5. Verify Grafana: no spike in error rate or latency

## Rollback Procedure

```bash
# Identify last known-good image SHA from Artifact Registry
gcloud artifacts docker images list \
  asia-southeast2-docker.pkg.dev/PROJECT_ID/pyhron/api

# Roll back Cloud Run to previous revision
gcloud run services update-traffic pyhron-api \
  --to-revisions=REVISION_NAME=100 \
  --region asia-southeast2

# Roll back database if migration was applied
alembic downgrade -1
```

## Incident Response

### API unhealthy (/health returns 503)

1. Check Cloud Run logs: `gcloud logging read "resource.type=cloud_run_revision"`
2. Check postgres connectivity: `psql $DATABASE_URL -c "SELECT 1"`
3. Check Redis connectivity: `redis-cli -u $REDIS_URL ping`
4. If DB unreachable: check Cloud SQL instance status in console
5. Escalate if not resolved in 15 minutes

### DLQ depth growing (Grafana alert)

1. Check validation-consumer logs for rejection reasons
2. If data quality issue: inspect dlq_permanent table
3. If transient network error: DLQ processor will retry automatically
4. If schema mismatch: requires code fix and redeployment

### Paper trading NAV frozen (no new snapshots)

1. Check paper-trading session status via API
2. Check celery-worker logs for task failures
3. Check Kafka consumer lag on pyhron.paper.nav_snapshot
4. Restart celery-worker if deadlocked

### Kill switch triggered unexpectedly

1. Check Redis: `redis-cli GET pyhron:kill_switch:global`
2. Check kill switch reason in live_trading_config table
3. Review portfolio_risk_snapshot for threshold breaches
4. If false positive: reset via API (ADMIN only) with documented reason
5. If legitimate: investigate the breach before resetting
