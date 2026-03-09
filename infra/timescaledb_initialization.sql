-- =============================================================================
-- Pyhron Platform — TimescaleDB Initialization
-- =============================================================================
-- Executed once on first docker-compose up via docker-entrypoint-initdb.d.
-- Creates all extensions and schemas required by the platform.
-- =============================================================================

-- Core extensions
CREATE EXTENSION IF NOT EXISTS timescaledb CASCADE;
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS pg_stat_statements;
CREATE EXTENSION IF NOT EXISTS btree_gist;

-- Schemas for domain separation
CREATE SCHEMA IF NOT EXISTS market_data;
CREATE SCHEMA IF NOT EXISTS trading;
CREATE SCHEMA IF NOT EXISTS risk;
CREATE SCHEMA IF NOT EXISTS macro;
CREATE SCHEMA IF NOT EXISTS commodity;
CREATE SCHEMA IF NOT EXISTS alternative_data;
CREATE SCHEMA IF NOT EXISTS fixed_income;
CREATE SCHEMA IF NOT EXISTS governance;
CREATE SCHEMA IF NOT EXISTS audit;
CREATE SCHEMA IF NOT EXISTS analytics;

-- Create mlflow database for MLflow tracking server
SELECT 'CREATE DATABASE mlflow OWNER pyhron'
WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'mlflow')\gexec
