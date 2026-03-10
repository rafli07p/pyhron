# Pyhron Quantitative Trading Platform — Comprehensive Technical Audit Report

**Date:** 2026-03-10
**Scope:** Full monorepo audit across all 11 directories, ~200 source files
**Auditor:** Automated deep-code analysis

---

## CRITICAL (Fix Before Any Live Trading)

### C-1. Hardcoded JWT Secrets in Multiple Locations
- **Files:**
  - `apps/api/api_middleware/jwt_authentication_middleware.py:22` — `JWT_SECRET_KEY = "CHANGE_ME_IN_PRODUCTION"`
  - `services/api/websocket_gateway/__init__.py:30-31` — `JWT_SECRET = "enthropy-jwt-secret"`
  - `shared/configuration_settings.py:35,69` — Default secrets: `"local-dev-secret-key-min-32-chars-long"`, `"local-dev-jwt-secret-change-in-prod-min-64"`
- **Risk:** SECURITY — Any attacker who reads the source can forge valid JWT tokens and gain full access to trading endpoints.
- **Fix:** Remove all default secrets; make `jwt_secret_key` and `app_secret_key` required fields (no defaults) in `Config`. Load exclusively from environment variables or secrets manager.

### C-2. Look-Ahead Bias in Backtesting Engine
- **File:** `strategy_engine/backtesting/idx_vectorbt_backtest_engine.py:116-126`
- **Description:** Signals are generated using data up to and including `rdate`, then target weights are applied starting from that same date (`target_weights.loc[rdate:, ...]`). This executes trades at the close of the signal bar — classic look-ahead bias.
- **Risk:** CORRECTNESS — All backtests produce unrealistically optimistic results. Strategies deployed based on these results will underperform.
- **Fix:**
  ```python
  # Generate signals using data up to T-1
  hist = market_data.loc[market_data.index.get_level_values(0) < rdate]
  signals = await strategy.generate_signals(hist, rdate)
  # Apply weights starting from T (execution at next bar's open)
  next_bar = market_data.index.get_level_values(0)[
      market_data.index.get_level_values(0) > rdate
  ][0]
  for sig in signals:
      target_weights.loc[next_bar:, sig.symbol] = sig.target_weight
  ```

### C-3. Walk-Forward Validator Does Not Optimize on In-Sample Window
- **File:** `strategy_engine/backtesting/idx_walk_forward_validator.py:136-155`
- **Description:** The validator only runs backtests on out-of-sample windows without any in-sample optimization step. This defeats the purpose of walk-forward analysis entirely.
- **Risk:** CORRECTNESS — Walk-forward results are meaningless; they're just sequential backtests, not validated parameter stability tests.
- **Fix:** Implement in-sample parameter optimization loop before each OOS test.

### C-4. Authentication Endpoints Are Stubs (login, register, refresh all raise exceptions)
- **File:** `apps/api/http_routers/user_authentication_router.py:58-98`
- **Description:** All auth endpoints (`/login`, `/register`, `/refresh`, `/me`) are stubs that raise `HTTPException`. No actual credential verification, password hashing, or token issuance occurs.
- **Risk:** SECURITY — The platform has no functional authentication system. The JWT middleware uses a hardcoded secret and there's no way to legitimately obtain tokens.
- **Fix:** Implement full auth flow: password hashing with bcrypt, user table queries, JWT token generation with proper claims, refresh token rotation with blacklisting.

### C-5. Trading, Strategy, and Backtest Endpoints All Lack Authorization
- **Files:**
  - `apps/api/http_routers/live_trading_position_router.py` — positions, orders, P&L, circuit breaker clear
  - `apps/api/http_routers/strategy_management_router.py` — strategy CRUD, enable/disable
  - `apps/api/http_routers/backtest_execution_router.py` — backtest submission and results
- **Description:** None of these routers use authentication dependencies. Any unauthenticated user can: view all positions/orders, clear circuit breakers, create/delete strategies, enable live trading, and submit computationally expensive backtests. No tenant isolation.
- **Risk:** SECURITY — Complete absence of access control on all trading and strategy management operations. Enables unauthorized trading, data theft, and resource exhaustion via backtest abuse.
- **Fix:** Add `Depends(require_role(Role.TRADER))` to all trading/strategy endpoints; `Depends(require_role(Role.ADMIN))` to circuit breaker clear and strategy enable/disable; add tenant_id filtering to all queries.

### C-6. Circuit Breaker Is Advisory Only — Not Enforced in Order Submission
- **File:** `services/order_management_system/order_submission_handler.py`
- **Description:** `CircuitBreakerStateManager` sets a Redis key when risk limits are breached, but `OrderSubmissionHandler` never checks this key before submitting orders. Orders can be submitted after a circuit breaker trips.
- **Risk:** CORRECTNESS — Risk limits can be violated during live trading, potentially causing catastrophic losses.
- **Fix:** Add circuit breaker check as the first step in `OrderSubmissionHandler.submit()`:
  ```python
  if await self._circuit_breaker.is_halted(strategy_id):
      raise RiskCheckFailedError("Circuit breaker is tripped", reasons=["trading_halted"])
  ```

### C-7. Float Arithmetic for VWAP / Average Fill Price Calculation
- **File:** `services/order_management_system/order_fill_event_processor.py:124-130`
- **Description:** Average fill price is computed using `float` arithmetic. Over thousands of fills, compounding rounding errors produce material discrepancies in portfolio cost basis.
- **Risk:** CORRECTNESS / DATA INTEGRITY — Cost basis drift leads to incorrect P&L reporting and potentially incorrect tax calculations.
- **Fix:** Replace all monetary variables with `Decimal`:
  ```python
  from decimal import Decimal
  current_avg = Decimal(str(order.avg_fill_price)) if order.avg_fill_price else Decimal("0")
  ```

### C-8. Hardcoded Database Credentials in Scripts and Alembic Config
- **Files:**
  - `scripts/setup_db.py:44` — `postgresql+asyncpg://enthropy:enthropy_secret@localhost:5432/enthropy`
  - `scripts/seed_data.py:72-76` — Same credentials
  - `data_platform/alembic_migrations/alembic.ini:3` — `postgresql+asyncpg://pyhron:pyhron@postgres:5432/pyhron`
- **Risk:** SECURITY — Credentials committed to source control.
- **Fix:** Remove all default credentials; require explicit `DATABASE_URL` environment variable with validation. In alembic.ini, use `%(DATABASE_URL)s` interpolation or leave blank (env.py already has env var fallback).

---

## HIGH (Fix Within 1 Sprint)

### H-1. CORS Wildcard Origins with Credentials Enabled
- **File:** `services/api/rest_gateway/__init__.py:305-312`
- **Description:** `allow_origins=["*"]` combined with `allow_credentials=True`. This allows any website to make authenticated cross-origin requests, enabling session hijacking and unauthorized trading actions.
- **Risk:** SECURITY — Any malicious site can steal user tokens and execute trades on their behalf.
- **Fix:** Replace wildcard with explicit allowed origins list: `allow_origins=get_settings().allowed_cors_origins` (e.g., `["https://app.pyhron.com"]`).

### H-2. IDX FIX Protocol Adapter is Entirely Stub
- **File:** `services/broker_connectivity/idx_fix_protocol_adapter.py:48-163`
- **Description:** All 6 methods raise `NotImplementedError`. If any code path routes to the IDX connector, it will crash.
- **Risk:** CORRECTNESS — Cannot execute trades on IDX.
- **Fix:** Implement FIX protocol adapter or add runtime guard preventing IDX routing.

### H-3. Reconciliation Workflow is Placeholder
- **File:** `.github/workflows/reconciliation-check.yaml:37-39`
- **Description:** The scheduled reconciliation job contains only `echo` statements — no actual position comparison logic.
- **Risk:** DATA INTEGRITY — No automated detection of position mismatches between internal state and broker.
- **Fix:** Implement actual reconciliation logic calling `PositionReconciliationMonitor`.

### H-4. Mypy and Security Scans Are Non-Blocking in CI
- **File:** `.github/workflows/ci.yaml:82-84,179,185`
- **Description:** Mypy, pip-audit, and TruffleHog all run with `continue-on-error: true`. Type errors, known vulnerabilities, and leaked secrets won't fail the CI pipeline.
- **Risk:** SECURITY / CODE QUALITY — Vulnerabilities and type errors silently pass.
- **Fix:** Remove `continue-on-error: true` from security and mypy steps.

### H-5. Max Drawdown Duration Calculation Bug
- **File:** `strategy_engine/backtesting/backtest_performance_metrics.py:136`
- **Description:** `duration = (trough_idx - peak_idx).days if hasattr(trough_idx, "days") else 0` — `trough_idx` is a pandas Timestamp, which doesn't have a `.days` attribute. Duration will always be 0.
- **Risk:** CORRECTNESS — Drawdown duration metric is permanently broken.
- **Fix:** `duration = (trough_idx - peak_idx).days if isinstance(trough_idx, pd.Timestamp) else 0`

### H-6. Redis Client Initialization Race Condition
- **File:** `shared/redis_cache_client.py:20-35`
- **Description:** Global `_redis_client` initialized without async lock. Multiple concurrent tasks could trigger double initialization.
- **Risk:** DATA INTEGRITY — Potential for multiple Redis client instances, leaking connections.
- **Fix:** Add `asyncio.Lock()` around initialization.

### H-7. Kafka Consumer Offset Reset Set to "earliest"
- **File:** `shared/kafka_producer_consumer.py:242`
- **Description:** `auto_offset_reset="earliest"` means every new consumer group reads entire topic history. In production with large topics, this causes startup delays and reprocessing.
- **Risk:** PERFORMANCE / DATA INTEGRITY — Accidental reprocessing of all historical messages.
- **Fix:** Use `"none"` in production to prevent accidental resets; document offset management strategy.

### H-8. Bollinger Strategy Has Conflicting Exit Logic
- **File:** `strategy_engine/idx_bollinger_mean_reversion_strategy.py:183,324`
- **Description:** `on_bar()` exits at 2% profit target; `generate_signals()` exits when close >= middle band. These are different conditions that will conflict in live execution.
- **Risk:** CORRECTNESS — Inconsistent behavior between backtest and live modes.
- **Fix:** Consolidate exit logic into a single consistent rule.

### H-9. Unpinned Docker Base Images
- **Files:** `infra/docker/Dockerfile:11,52`, `infra/docker/api_service.Dockerfile:4,39`, `infra/docker/celery_worker.Dockerfile:4,39`
- **Description:** All images use `python:3.12-slim` without digest pinning. Docker-compose uses `timescale/timescaledb:latest-pg16`.
- **Risk:** SECURITY — Supply chain attack vector; unreproducible builds.
- **Fix:** Pin all images to specific SHA256 digests.

### H-10. Duplicate ORM Model Definitions Create Schema Mismatch Risk
- **Files:** `data_platform/database_models/*.py` vs `data_platform/models/market.py` and `data_platform/models/trading.py`
- **Description:** Two parallel sets of ORM models exist with different table names (e.g., `idx_equity_instruments` in migrations vs `instruments` in `models/market.py`). Creates maintenance burden, import confusion, and potential schema drift.
- **Risk:** DATA INTEGRITY — Code may write to wrong table or use wrong schema.
- **Fix:** Consolidate to a single model definition source. Keep `database_models/` (matches migrations) and delete or repurpose `models/`.

### H-11. `datetime.utcnow` (Timezone-Naive) Used in ORM Model Defaults
- **Files:** `data_platform/database_models/idx_equity_instrument.py:58`, `data_platform/models/market.py:117`
- **Description:** `onupdate=datetime.utcnow` produces timezone-naive datetime objects. When mixed with tz-aware timestamps from `TIMESTAMP(timezone=True)` columns, comparisons will raise `TypeError`.
- **Risk:** DATA INTEGRITY — Runtime crashes on timestamp comparison.
- **Fix:** Replace with `onupdate=lambda: datetime.now(timezone.utc)`

### H-12. Missing OHLCV Data Validation Constraints in Database
- **File:** `data_platform/database_models/idx_equity_ohlcv_tick.py`, migration `002`
- **Description:** No `CHECK` constraints ensuring `high >= low`, `volume >= 0`, or price ordering (`low <= open/close <= high`). All OHLC columns are nullable.
- **Risk:** DATA INTEGRITY — Invalid price bars (e.g., `low > high`) can be persisted and corrupt strategy signals.
- **Fix:** Add database-level CHECK constraints: `CHECK (low <= high)`, `CHECK (volume IS NULL OR volume >= 0)`.

### H-13. No SQLAlchemy Relationships Defined — N+1 Query Risk
- **Files:** All `data_platform/database_models/*.py`
- **Description:** Foreign keys exist (e.g., `idx_equity_financial_statement.symbol → idx_equity_instruments.symbol`) but no SQLAlchemy `relationship()` properties. Any code iterating over statements and accessing instrument data will execute N+1 queries.
- **Risk:** PERFORMANCE — Database query amplification under load.
- **Fix:** Add `relationship()` with `lazy="selectin"` or `lazy="joined"` for common access patterns.

### H-14. Synchronous yfinance Call Blocks Async Event Loop
- **File:** `data_platform/equity_ingestion/idx_equity_end_of_day_ingestion.py:281-287`
- **Description:** `yfinance.Ticker.history()` is synchronous and blocks the asyncio event loop during data fetching.
- **Risk:** PERFORMANCE — Freezes all concurrent async operations during fetch.
- **Fix:** Wrap in `asyncio.to_thread()` or use async HTTP client with Polygon API.

---

## MEDIUM (Fix Within 1 Month)

### M-1. No Survivorship Bias Prevention in Strategies
- **Description:** No mechanism validates that backtested universe only includes stocks that were actually listed during the test period. Delisted/IPO'd stocks are not filtered.
- **Files:** All 5 strategy files in `strategy_engine/`
- **Fix:** Add IPO date / delisting date validation against historical universe.

### M-2. Missing Slippage Model in Backtesting
- **File:** `strategy_engine/backtesting/idx_transaction_cost_model.py`
- **Description:** Only fixed commission and tax modeled. No bid-ask spread, market impact, or partial fill simulation.
- **Fix:** Add configurable slippage model (e.g., 5-10bps for IDX mid/large-cap).

### M-3. Prometheus Metrics Use Float for IDR Monetary Values
- **File:** `shared/prometheus_metrics_registry.py:31`
- **Description:** `Gauge` metrics for P&L use float, which loses precision for large IDR values (trillions).
- **Fix:** Report metrics in integer smallest units (e.g., IDR without decimals).

### M-4. WebSocket Token Passed in URL Query String
- **File:** `services/api/websocket_gateway/__init__.py:369`
- **Description:** JWT token passed as query parameter is logged in access logs — security anti-pattern.
- **Fix:** Accept token in first WebSocket message or via header.

### M-5. No Rate Limiting on Authentication Endpoints
- **File:** `apps/api/http_routers/user_authentication_router.py:58-88`
- **Description:** Login, register, and refresh endpoints have no rate limiting. Auth paths are in the `PUBLIC_PATHS` set and bypass the global rate limiter. Enables brute-force password attacks and credential stuffing.
- **Fix:** Add `@limiter.limit("5/minute")` per IP for login; implement per-account lockout after 3 failed attempts.

### M-6. Rate Limiter Race Condition in Redis
- **File:** `apps/api/api_middleware/per_ip_rate_limiter.py:65-67`
- **Description:** `INCR` + separate `EXPIRE` is not atomic. Under high concurrency, keys may never expire.
- **Fix:** Use Lua script for atomic increment-with-expiry.

### M-7. No CSRF Protection on State-Changing Endpoints
- **Description:** The React frontend makes POST/PUT/DELETE requests without CSRF tokens. The FastAPI backend does not validate CSRF tokens. Combined with the CORS wildcard issue (H-1), this enables cross-site request forgery attacks on trading operations.
- **Fix:** Implement double-submit cookie pattern; add CSRF middleware to FastAPI.

### M-8. Missing HTTP Security Headers
- **Description:** No Content-Security-Policy, X-Frame-Options, X-Content-Type-Options, HSTS, or Referrer-Policy headers set. Leaves the platform vulnerable to clickjacking, MIME sniffing, and protocol downgrade attacks.
- **Fix:** Add security headers middleware to FastAPI.

### M-9. Database Port Exposure in Docker Compose
- **File:** `infra/docker/docker-compose.yaml:26,50,99`
- **Description:** PostgreSQL (5432), Redis (6379), and Kafka (9092) ports mapped to host.
- **Fix:** Remove port mappings; access via Docker network only.

### M-10. Incomplete Kubernetes Security Context
- **File:** `infra/kubernetes/deployment.yaml:44-48`
- **Description:** Missing `readOnlyRootFilesystem`, `allowPrivilegeEscalation: false`, and `capabilities.drop: ["ALL"]`.
- **Fix:** Add full security context.

### M-11. Hardcoded Commodity/Equity Company Profiles
- **Files:** `commodity_linkage_engine/commodity_sensitivity_models/*.py`
- **Description:** Coal miner, plantation, energy company profiles with production data and exchange rates hardcoded for 2024. Will become stale.
- **Fix:** Move to database-backed or config-file-based reference data with quarterly update process.

### M-12. Kelly Criterion Uses Confidence as Win Probability
- **File:** `strategy_engine/live_execution/strategy_position_sizer.py:92-111`
- **Description:** Model confidence score is treated as win probability, which is incorrect. Win/loss ratio is hardcoded at 1.5.
- **Fix:** Derive win rate and W/L ratio from historical backtest statistics per strategy.

### M-13. Missing Health Checks for Celery Workers
- **File:** `infra/docker/docker-compose.yaml`
- **Description:** `worker` and `beat` services have no health check defined.
- **Fix:** Add Celery inspect-based health checks.

---

## LOW (Tech Debt / Nice-to-Have)

### L-1. Copyright/Name Inconsistency & Documentation Stale References
- `LICENSE:3` says "Enthropy" but project is "Pyhron". `.gitignore:2` also says "Enthropy".
- All docs reference `src/enthropy/` import paths that don't exist (see Documentation Discrepancies D-1, D-3).

### L-2. docker-compose.override.yml in .gitignore but Tracked in Repo
- Contradiction between `.gitignore` (line 68) and the file existing in version control.

### L-3. Ruff Security Rule Overrides
- `pyproject.toml` ignores `S105` (hardcoded passwords), `S110` (bare except pass), `S104` (bind all interfaces), `S108` (/tmp usage).

### L-4. No Minimum Test Coverage Threshold
- `pyproject.toml` configures coverage reporting but no `--cov-fail-under` minimum.

### L-5. Many Scaffold Directories with Empty `__init__.py`
- `apps/admin-console/`, `apps/research-platform/`, `apps/terminal/`, `services/execution/`, `services/portfolio/`, `services/research/`, `services/risk/` — all contain only empty `__init__.py` files.

### L-6. Missing Pre-commit Hooks
- No `mypy`, `bandit`, or `gitleaks` hooks in `.pre-commit-config.yaml`.

### L-7. Value Factor Z-Score Epsilon Too Small
- `strategy_engine/idx_value_factor_strategy.py:171-172` — Uses `1e-9` epsilon for std dev division guard. Should use `1e-6` or handle zero-std explicitly.

### L-8. Kalman Filter State Persists Across Backtests
- `strategy_engine/idx_pairs_cointegration_strategy.py:114` — `_kalman_filters` dict not reset between runs.

### L-9. Multiple `RequestLoggingMiddleware` Implementations
- Duplicate in `services/api/rest_gateway/__init__.py` and `services/api/logging/__init__.py`.

### L-10. Missing Request ID Propagation
- No `X-Request-ID` header tracking through the request lifecycle for distributed tracing.

---

## DOCUMENTATION DISCREPANCIES

### D-1. System Name Mismatch — "Enthropy" vs "Pyhron"
- Documentation references "**Enthropy**" in 20+ locations (API docs, compliance guides, architecture overview)
- Actual codebase is named "**Pyhron**" (repository, Docker containers, config files)
- Docs reference `src/enthropy/` import paths (e.g., `from enthropy.compliance.engine import ComplianceEngine`) but actual code lives at `/services/risk/compliance/`
- **Impact:** Onboarding confusion; import paths in compliance/API docs are non-functional

### D-2. ADR #006 (vectorbt) Status Incorrect
- Marked as **"Proposed"** but implementation is fully built at `strategy_engine/backtesting/idx_vectorbt_backtest_engine.py`
- Should be updated to **"Accepted"**

### D-3. Documented Paths Don't Match Actual Structure
- Docs reference `src/enthropy/shared/encryption/service.py` — actual encryption code at `shared/encryption/` (if it exists) or `data_platform/encryption/` (empty stub)
- Docs reference `src/enthropy/compliance/data_subject.py` — actual compliance code at `services/risk/compliance/__init__.py`
- Getting started guide references `src/enthropy/backtest/` — actual location is `strategy_engine/backtesting/`

### D-4. Features Documented but Not Implemented
- **gRPC support** — Architecture docs say "gRPC (future)" but no gRPC code exists
- **Polygon.io API** — Getting started mentions Polygon as a data source, but `.env.example` only has EODHD
- **Alpaca US trading** — Docs reference Alpaca for US markets, but platform is IDX-focused

### D-5. Operational Runbook — Good Practices
- No hardcoded secrets in runbook (uses `registry.example.com` placeholder) ✓
- `.env.example` uses `REPLACE-with-*` placeholders for all sensitive values ✓
- Commands use dynamic values (`$(git rev-parse --short HEAD)`) ✓

---

## MISSING IMPLEMENTATIONS

| Feature | Reference | Status |
|---------|-----------|--------|
| User authentication (login/register/refresh) | `user_authentication_router.py` | Stub — all endpoints raise exceptions |
| IDX FIX protocol connectivity | `idx_fix_protocol_adapter.py` | Stub — all methods raise `NotImplementedError` |
| Position reconciliation logic | `reconciliation-check.yaml` | Placeholder echo statements |
| Walk-forward in-sample optimization | `idx_walk_forward_validator.py` | Only OOS runs, no IS optimization |
| Admin console (risk monitor, strategy manager, system health, user management) | `apps/admin-console/` | Empty `__init__.py` files only |
| Research platform (backtest UI, datasets, factor lab, ML pipelines, notebooks) | `apps/research-platform/` | Empty `__init__.py` files only |
| Terminal application (charts, panels, command palette) | `apps/terminal/` | Empty `__init__.py` files only |
| Execution engine internals (order router, trade matching) | `services/execution/` | Empty `__init__.py` (but partial implementation exists in `__init__.py` of sub-packages) |
| Portfolio services (exposure tracking, P&L engine, positions) | `services/portfolio/` | Partial — some implemented, some stubs |
| Risk compliance, post-trade analytics | `services/risk/` | Empty stubs |
| Data quality validation module | `data_platform/quality/` | Empty `__init__.py` |
| Data encryption module | `data_platform/encryption/` | Empty `__init__.py` |
| Data backup module | `data_platform/backup/` | Empty `__init__.py` |
| Gaikindo vehicle sales HTML parsing | `gaikindo_vehicle_sales_ingestion.py` | Returns empty list |
| CPO BMD settlement parsing | `cpo_price_mpob_ingestion.py` | Returns empty list |
| OJK governance HTML parsing | `idx_equity_governance_flag_ingestion.py` | Returns empty list |
| ESDM oil/gas lifting parsing | `esdm_energy_production_ingestion.py` | Returns empty list |
| DataSubjectService (UU PDP data rights) | `docs/compliance/uu_pdp_guide.md:136-166` | Not implemented — `export_user_data()`, `purge_user_data()` documented but no code |
| AML transaction monitoring | `docs/compliance/sec_ojk_reporting.md:113-144` | Not implemented — IDR 500M threshold checks, PPATK/OFAC screening, `file_suspicious_report()` |
| CAT (Consolidated Audit Trail) reporting | `docs/compliance/sec_ojk_reporting.md:50-69` | Not implemented — `get_cat_events()` for SEC compliance |
| FieldEncryptor (granular PII encryption) | `docs/compliance/uu_pdp_guide.md:49-58` | Not implemented — only bulk `EncryptionService` exists |
| Scheduled compliance report generation | `docs/compliance/sec_ojk_reporting.md:203-222` | Not implemented — no cron scheduler for SEC 13F, OJK daily reports |
| S3 encrypted report export | `docs/compliance/sec_ojk_reporting.md:154-155` | Not implemented — `export_report(encrypt=True)` with S3 storage |
| Yield curve interpolation & bond pricing | `docs/database_schema_dictionary.md:288-309` | Schema exists, no pricing/analytics engine |

---

## POSITIVE FINDINGS

1. **Strong type system** — Pydantic V2 models with frozen classes, comprehensive type hints, mypy strict mode enabled
2. **Proper Decimal usage in database models** — All price/monetary columns use `Numeric(18,6)` or `Numeric(20,4)`, not float
3. **Timezone-aware timestamps in database** — All `TIMESTAMP(timezone=True)` in migrations and models
4. **Comprehensive Kafka architecture** — Idempotent producers (`acks="all"`, `enable_idempotence=True`), dead letter queues, manual offset commits
5. **Well-designed exception hierarchy** — `PyhronError` base with domain-specific subclasses (`RiskCheckFailedError`, `OrderRejectedError`, etc.)
6. **Multi-tenant security model** — `tenant_id` in all event schemas, RBAC with `require_role()` and `require_tenant()` decorators
7. **Order state machine correctness** — Explicit `VALID_TRANSITIONS` dict with terminal states; comprehensive unit tests for valid/invalid paths
8. **Pre-trade risk checks** — Position limits, sector concentration, buying power, lot size validation — all with well-structured unit tests
9. **Structured JSON logging** — `structlog` with ISO timestamps, service context, production-ready JSON output
10. **Good CI pipeline structure** — Proto compilation verification, lint + format + type check, test with Postgres/Redis services, security scanning, Docker build
11. **Proper composite indexes** — `(symbol, time)` composite indexes on OHLCV hypertable for efficient time-series queries
12. **TimescaleDB hypertable design** — Proper partitioning by time with 7-day chunks for market data
13. **IDX domain expertise** — Correct lot size (100 shares), T+2 settlement modeling, IDX-specific tax/commission rates (0.15% buy, 0.25% sell)
14. **Protobuf contracts** — Language-agnostic service boundaries enabling planned Rust migration
15. **Docker multi-stage builds** — Non-root users, slim base images, proper layer caching

---

## METRICS SUMMARY

| Dimension | Score (1-10) | Key Issues |
|-----------|:---:|---|
| **Security** | 2 | Hardcoded JWT secrets (3 locations), CORS wildcard + credentials, stub auth, no authz on trading endpoints, no CSRF, credentials in scripts |
| **Trading Logic Correctness** | 4 | Look-ahead bias in backtest, walk-forward broken, conflicting exit logic, advisory-only circuit breaker |
| **Data Integrity** | 6 | Good DB schema design, tz-aware timestamps, but float VWAP calculation, no data quality validation module |
| **Code Quality** | 7 | Strong typing, good patterns, structured logging; but float for money in some paths, dead code |
| **Test Coverage** | 4 | ~25-30% estimated coverage; E2E tests disabled; zero tests for strategies, broker adapters, API auth, ingestion; no backtest regression snapshots |
| **Infrastructure** | 6 | Good K8s/Terraform foundation; unpinned images, exposed ports, incomplete security context |
| **Performance** | 6 | Proper async patterns, TimescaleDB; but blocking yfinance, no batch inserts, single-threaded executors |
| **Overall** | **5** | Solid architectural foundation with critical security and correctness gaps blocking production |

---

## PRIORITY ACTION PLAN

| # | Action | Effort (hrs) | Impact |
|---|--------|:---:|---|
| 1 | Remove all hardcoded JWT secrets; require env-only configuration | 2 | Eliminates authentication bypass |
| 2 | Fix look-ahead bias in backtest engine (T-1 data, T+1 execution) | 4 | Makes backtest results realistic |
| 3 | Implement circuit breaker enforcement in OrderSubmissionHandler | 2 | Prevents post-breach trading |
| 4 | Replace float with Decimal in all monetary calculations (VWAP, P&L, fill processor) | 8 | Eliminates cost basis drift |
| 5 | Implement user authentication flow (login, register, refresh with bcrypt + JWT) | 16 | Enables actual access control |
| 6 | Add role enforcement to trading endpoints (positions, orders, circuit breaker) | 4 | Prevents unauthorized trading actions |
| 7 | Fix walk-forward validator to include in-sample optimization | 8 | Enables proper strategy validation |
| 8 | Remove `continue-on-error` from CI security/type-check steps | 1 | Enforces security gates |
| 9 | Pin Docker image digests and remove database port mappings | 2 | Closes supply chain and network attack vectors |
| 10 | Add slippage model to backtesting and fix max drawdown duration bug | 6 | Improves backtest accuracy |

**Total estimated effort for top 10: ~53 hours**

---

## MODULES WITH ZERO TEST COVERAGE

**Estimated overall coverage: 25-30%** (33 test files, ~5,600 lines, 450+ test functions)
**E2E tests all disabled** via `@SKIP_E2E` — never run in CI

| Module | Files | Criticality |
|--------|-------|-------------|
| `strategy_engine/idx_*.py` (all 5 strategies) | 5 | HIGH — No signal generation, parameter edge case, or regime tests |
| `strategy_engine/backtesting/` | 4 | HIGH — No backtest engine or walk-forward tests; no regression snapshots |
| `strategy_engine/live_execution/` | 2 | HIGH — No position sizer / signal publisher tests |
| `services/broker_connectivity/` | 4 | HIGH — No broker adapter tests (Alpaca, IDX FIX) |
| `services/execution/` | 4 | HIGH — No exchange connector, order router, or trade matching tests |
| `services/order_management_system/` (handlers) | 4 | HIGH — OMS state machine tested, but submission handler, fill processor, timeout monitor untested |
| `services/pre_trade_risk_engine/` (engine) | 3 | MEDIUM — Individual checks tested, but circuit breaker manager, VaR calculator, Kafka consumer untested |
| `apps/api/api_middleware/` | 4 | HIGH — No middleware tests (JWT validation, rate limiter, subscription tier) |
| `apps/api/http_routers/` | 12 | HIGH — No endpoint tests; no auth flow tests at all |
| `data_platform/*_ingestion/` | 20+ | MEDIUM — No ingestion pipeline tests |
| `commodity_linkage_engine/` | 12 | MEDIUM — Only `cpo_plantation` sensitivity tested |
| `governance_intelligence/` | 5 | LOW — No governance analyzer tests |
| `macro_intelligence/` | 5 | LOW — No macro analysis tests |

### What IS Well-Tested
- Order state machine transitions (2 dedicated test files, exhaustive valid/invalid path coverage)
- Pre-trade risk checks (position limits, concentration, buying power, lot size — excellent edge cases)
- P&L engine (553 lines — realized/unrealized PnL, fees, fractional quantities, uses Decimal correctly)
- OHLCV quality validation (high/low ordering, zero prices, doji bars, timestamp ordering)
- Encryption (AES-256-GCM roundtrip, tampering detection, key rotation, UU PDP compliance)
- IDX trading calendar (weekends, 11 Indonesian holidays, T+2 settlement)
- Transaction cost model (buy 0.15%, sell 0.25%, lot rounding)
- Risk limit schemas (Pydantic validation with Decimal, boundary conditions)

---

## TODOs AND FIXMEs FOUND

| File | Line | Content |
|------|------|---------|
| `services/api/rest_gateway/__init__.py` | 358 | `# TODO: verify downstream dependencies (DB, Redis, Kafka)` |
| `services/execution/execution_engine/__init__.py` | 163-166 | Commented-out Rust/Go FFI integration point |
| `data_platform/alternative_data_ingestion/gaikindo_vehicle_sales_ingestion.py` | 172-175 | `# Simplified table extraction -- real implementation would use a proper HTML parser` |
| `data_platform/commodity_ingestion/cpo_price_mpob_ingestion.py` | 281-283 | `# Placeholder for actual BMD parsing logic` — returns empty list |
| `data_platform/equity_ingestion/idx_equity_governance_flag_ingestion.py` | 285-288 | `# Placeholder: real implementation would use lxml` — returns empty list |
| `data_platform/macro_ingestion/esdm_energy_production_ingestion.py` | 405-407 | `# Simplified: real implementation would parse structured tables` — returns empty list |
| `macro_intelligence/apbn_fiscal_health_analyzer.py` | 128 | Dead code — `total_budget` variable computed but never used |
