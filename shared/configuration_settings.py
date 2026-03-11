"""Pyhron platform configuration.

Centralised settings loaded from environment variables and ``.env`` files
using Pydantic v2 ``BaseSettings``. Validates at startup — fail fast.

Usage::

    from shared.configuration_settings import get_config

    config = get_config()
    print(config.database_url)
"""

from __future__ import annotations

from functools import lru_cache
from typing import Any

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings


class Config(BaseSettings):
    """Application-wide settings for the Pyhron platform."""

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "case_sensitive": False,
        "extra": "ignore",
    }

    # -- General --
    app_name: str = Field(default="pyhron", max_length=64, description="Application name")
    app_env: str = Field(default="development", description="Deployment environment")
    app_secret_key: str = Field(default="local-dev-secret-key-min-32-chars-long", min_length=32)
    app_debug: bool = Field(default=False)
    app_host: str = Field(default="0.0.0.0")
    app_port: int = Field(default=8000)
    log_level: str = Field(default="INFO")

    # -- Database --
    database_url: str = Field(
        default="postgresql+asyncpg://pyhron:pyhron@localhost:5432/pyhron",
    )
    database_sync_url: str = Field(
        default="postgresql+psycopg://pyhron:pyhron@localhost:5432/pyhron",
    )
    database_pool_size: int = Field(default=20, ge=1, le=200)
    database_max_overflow: int = Field(default=10, ge=0, le=100)
    database_pool_timeout: int = Field(default=30, ge=1)

    # -- Redis --
    redis_url: str = Field(default="redis://localhost:6379/0")
    celery_broker_url: str = Field(default="redis://localhost:6379/1")
    celery_result_backend: str = Field(default="redis://localhost:6379/2")

    # -- Kafka --
    kafka_bootstrap_servers: str = Field(default="localhost:9092")
    kafka_consumer_group: str = Field(default="pyhron-consumers")

    # -- Market Data --
    bps_api_key: str = Field(default="")
    nasa_firms_api_key: str = Field(default="")
    globalcoal_api_key: str = Field(default="")
    eodhd_api_key: str = Field(default="")
    polygon_api_key: str = Field(default="")
    alpaca_api_key: str = Field(default="")
    alpaca_secret_key: str = Field(default="")
    alpaca_base_url: str = Field(default="https://paper-api.alpaca.markets")

    # -- JWT / Auth --
    jwt_secret_key: str = Field(default="local-dev-jwt-secret-change-in-prod-min-64", min_length=32)
    jwt_algorithm: str = Field(default="HS256")
    jwt_access_token_expire_minutes: int = Field(default=15, ge=1)
    jwt_refresh_token_expire_days: int = Field(default=7, ge=1)

    # -- Risk Engine --
    risk_max_position_size_pct: float = Field(default=0.10)
    risk_max_sector_concentration_pct: float = Field(default=0.30)
    risk_daily_loss_limit_pct: float = Field(default=0.02)
    risk_max_orders_per_minute: int = Field(default=60)
    risk_max_var_95_pct: float = Field(default=0.05)
    risk_idx_lot_size: int = Field(default=100)

    # -- MLflow --
    mlflow_tracking_uri: str = Field(default="http://localhost:5000")
    mlflow_experiment_name: str = Field(default="pyhron-strategies")

    # -- Monitoring --
    sentry_dsn: str = Field(default="")
    prometheus_port: int = Field(default=9090)

    # -- CORS --
    allowed_cors_origins: str = Field(
        default="http://localhost:3000", description="Comma-separated allowed CORS origins"
    )

    # -- Notifications --
    slack_webhook_url: str = Field(default="")
    alert_email: str = Field(default="")

    @field_validator("app_secret_key")
    @classmethod
    def _validate_app_secret(cls, v: str, info: Any) -> str:
        _dev_defaults = {"local-dev-secret-key-min-32-chars-long"}
        if info.data.get("app_env") == "production" and v in _dev_defaults:
            msg = "app_secret_key must be changed from the default in production"
            raise ValueError(msg)
        return v

    @field_validator("jwt_secret_key")
    @classmethod
    def _validate_jwt_secret(cls, v: str, info: Any) -> str:
        _dev_defaults = {"local-dev-jwt-secret-change-in-prod-min-64"}
        if info.data.get("app_env") == "production" and v in _dev_defaults:
            msg = "jwt_secret_key must be changed from the default in production"
            raise ValueError(msg)
        return v

    @field_validator("database_url")
    @classmethod
    def _validate_database_url(cls, v: str) -> str:
        valid = ("postgresql", "sqlite")
        if not any(v.startswith(p) for p in valid):
            msg = f"database_url must start with one of {valid}, got: {v[:30]}"
            raise ValueError(msg)
        return v

    @field_validator("kafka_bootstrap_servers")
    @classmethod
    def _validate_kafka(cls, v: str) -> str:
        servers = [s.strip() for s in v.split(",") if s.strip()]
        if not servers:
            raise ValueError("kafka_bootstrap_servers must contain at least one broker")
        return ",".join(servers)

    @property
    def is_production(self) -> bool:
        return self.app_env == "production"

    @property
    def is_development(self) -> bool:
        return self.app_env == "development"

    @property
    def kafka_brokers(self) -> list[str]:
        return [s.strip() for s in self.kafka_bootstrap_servers.split(",")]


@lru_cache(maxsize=1)
def get_config() -> Config:
    """Return the cached application config singleton."""
    return Config()
