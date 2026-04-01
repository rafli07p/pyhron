# Data Dictionary — New Tables

## `ml.ml_model_runs`
Lightweight local index of MLflow runs for fast lookups.

| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| id | UUID | PK | Auto-generated UUID |
| model_name | VARCHAR(128) | NOT NULL | Model identifier (e.g. `xgb_ranker`) |
| mlflow_run_id | VARCHAR(64) | NOT NULL, UNIQUE | MLflow run identifier |
| registered_at | TIMESTAMPTZ | NOT NULL | When the model was registered |
| feature_names | JSONB | NOT NULL | List of feature names used |
| metrics | JSONB | NOT NULL | Performance metrics dict |
| is_active | BOOLEAN | DEFAULT FALSE | Currently active model flag |

**Indexes**: `(model_name, registered_at DESC)`

## `trading.execution_schedules`
Persisted child order schedules from execution algorithms.

| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| id | UUID | PK | Auto-generated UUID |
| parent_order_id | UUID | NOT NULL | FK to `trading.orders` |
| algorithm | VARCHAR(32) | NOT NULL | Algorithm name (TWAP/VWAP/POV/IS) |
| parameters | JSONB | NOT NULL | Algorithm configuration |
| child_orders | JSONB | NOT NULL | List of scheduled child orders |
| created_at | TIMESTAMPTZ | NOT NULL | Schedule creation time |
| status | VARCHAR(16) | NOT NULL | pending/active/completed/cancelled |

**Check constraint**: `status IN ('pending', 'active', 'completed', 'cancelled')`

## `portfolio.portfolio_snapshots`
Historical portfolio weight records for PIT rebalance analysis.
TimescaleDB hypertable on `snapshot_at`.

| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| id | UUID | PK | Auto-generated UUID |
| snapshot_at | TIMESTAMPTZ | NOT NULL | Snapshot timestamp (hypertable key) |
| method | VARCHAR(32) | NOT NULL | Optimization method used |
| weights | JSONB | NOT NULL | Asset weight dict |
| expected_return | DOUBLE | YES | Annualised expected return |
| expected_vol | DOUBLE | YES | Annualised expected volatility |
| turnover | DOUBLE | YES | Portfolio turnover fraction |
| cost_bps | DOUBLE | YES | Estimated cost in basis points |
