-- =============================================================================
-- Pyhron — TimescaleDB Initialization
-- =============================================================================
-- Executed once on first docker-compose up via docker-entrypoint-initdb.d.
-- Creates extensions and schemas required by the platform.
-- =============================================================================

-- Extensions
CREATE EXTENSION IF NOT EXISTS timescaledb CASCADE;
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS pg_stat_statements;
CREATE EXTENSION IF NOT EXISTS btree_gist;

-- Schemas
CREATE SCHEMA IF NOT EXISTS trading;
CREATE SCHEMA IF NOT EXISTS market_data;
CREATE SCHEMA IF NOT EXISTS risk;
CREATE SCHEMA IF NOT EXISTS audit;
CREATE SCHEMA IF NOT EXISTS analytics;

-- Create mlflow database for MLflow tracking server
SELECT 'CREATE DATABASE mlflow OWNER pyhron'
WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'mlflow')\gexec
