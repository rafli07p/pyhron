"""Enthropy platform configuration.

Centralised settings loaded from environment variables and ``.env``
files using Pydantic v2 ``BaseSettings``.  Validates all configuration
at startup so misconfigurations fail fast.

Usage::

    from shared.configs import get_settings

    settings = get_settings()
    print(settings.database_url)
"""

from __future__ import annotations

from enum import StrEnum
from functools import lru_cache
from typing import Optional

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings


class Environment(StrEnum):
    """Deployment environment."""

    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"
    TESTING = "testing"


class LogLevel(StrEnum):
    """Supported log levels."""

    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class Settings(BaseSettings):
    """Application-wide settings for the Enthropy platform.

    Values are loaded from environment variables and ``.env`` files.
    Sensitive defaults are intentionally left empty so deployment
    pipelines must provide them explicitly.
    """

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "env_prefix": "ENTHROPY_",
        "case_sensitive": False,
        "extra": "ignore",
    }

    # -- General --
    app_name: str = Field(default="enthropy", max_length=64, description="Application name")
    environment: Environment = Field(default=Environment.DEVELOPMENT, description="Deployment environment")
    debug: bool = Field(default=False, description="Enable debug mode")
    log_level: LogLevel = Field(default=LogLevel.INFO, description="Logging level")
    secret_key: str = Field(default="CHANGE-ME-IN-PRODUCTION", min_length=8, description="Application secret key")

    # -- Database --
    database_url: str = Field(
        default="postgresql+asyncpg://enthropy:enthropy@localhost:5432/enthropy",
        description="Primary database connection URL",
    )
    database_pool_size: int = Field(default=20, ge=1, le=200, description="Database connection pool size")
    database_max_overflow: int = Field(default=10, ge=0, le=100, description="Max overflow connections")
    database_echo: bool = Field(default=False, description="Echo SQL statements (debug)")

    # -- Redis --
    redis_url: str = Field(
        default="redis://localhost:6379/0",
        description="Redis connection URL",
    )
    redis_max_connections: int = Field(default=50, ge=1, le=500, description="Redis connection pool size")
    redis_socket_timeout: float = Field(default=5.0, gt=0, description="Redis socket timeout in seconds")

    # -- Kafka / event bus --
    kafka_bootstrap_servers: str = Field(
        default="localhost:9092",
        description="Comma-separated Kafka broker addresses",
    )
    kafka_consumer_group: str = Field(default="enthropy-default", description="Kafka consumer group ID")
    kafka_auto_offset_reset: str = Field(default="latest", description="Kafka auto offset reset policy")

    # -- API keys (external providers) --
    bloomberg_api_key: Optional[str] = Field(default=None, description="Bloomberg B-PIPE / BLPAPI key")
    refinitiv_api_key: Optional[str] = Field(default=None, description="Refinitiv / LSEG API key")
    polygon_api_key: Optional[str] = Field(default=None, description="Polygon.io API key")
    alpaca_api_key: Optional[str] = Field(default=None, description="Alpaca trading API key")
    alpaca_api_secret: Optional[str] = Field(default=None, description="Alpaca trading API secret")
    openai_api_key: Optional[str] = Field(default=None, description="OpenAI API key (for NLP research)")
    anthropic_api_key: Optional[str] = Field(default=None, description="Anthropic API key")

    # -- JWT / Auth --
    jwt_secret_key: str = Field(
        default="CHANGE-ME-jwt-secret",
        min_length=16,
        description="JWT signing secret",
    )
    jwt_algorithm: str = Field(default="HS256", description="JWT signing algorithm")
    jwt_access_token_expire_minutes: int = Field(default=30, ge=1, description="Access token TTL in minutes")
    jwt_refresh_token_expire_days: int = Field(default=7, ge=1, description="Refresh token TTL in days")

    # -- S3 / Object storage --
    s3_bucket_name: str = Field(default="enthropy-data", description="S3 bucket for data storage")
    s3_region: str = Field(default="us-east-1", description="AWS region")
    aws_access_key_id: Optional[str] = Field(default=None, description="AWS access key")
    aws_secret_access_key: Optional[str] = Field(default=None, description="AWS secret key")

    # -- Feature flags --
    feature_live_trading: bool = Field(default=False, description="Enable live trading (vs. paper only)")
    feature_options_trading: bool = Field(default=False, description="Enable options trading")
    feature_crypto_trading: bool = Field(default=False, description="Enable crypto trading")
    feature_ml_signals: bool = Field(default=False, description="Enable ML-based signal generation")
    feature_realtime_risk: bool = Field(default=True, description="Enable real-time risk monitoring")
    feature_audit_logging: bool = Field(default=True, description="Enable audit logging")

    # -- Rate limits --
    api_rate_limit_per_minute: int = Field(default=600, ge=1, description="API requests per minute per user")
    market_data_rate_limit_per_second: int = Field(default=100, ge=1, description="Market data requests per second")

    # -- Monitoring --
    sentry_dsn: Optional[str] = Field(default=None, description="Sentry DSN for error tracking")
    prometheus_port: int = Field(default=9090, ge=1, le=65535, description="Prometheus metrics port")
    enable_tracing: bool = Field(default=False, description="Enable OpenTelemetry tracing")

    # -----------------------------------------------------------------------
    # Validators
    # -----------------------------------------------------------------------

    @field_validator("database_url")
    @classmethod
    def _validate_database_url(cls, v: str) -> str:
        """Ensure the database URL uses a supported scheme."""
        valid_prefixes = ("postgresql", "sqlite", "mysql")
        if not any(v.startswith(prefix) for prefix in valid_prefixes):
            raise ValueError(
                f"database_url must start with one of {valid_prefixes}, got: {v[:30]}..."
            )
        return v

    @field_validator("redis_url")
    @classmethod
    def _validate_redis_url(cls, v: str) -> str:
        if not v.startswith(("redis://", "rediss://")):
            raise ValueError("redis_url must start with redis:// or rediss://")
        return v

    @field_validator("kafka_bootstrap_servers")
    @classmethod
    def _validate_kafka_servers(cls, v: str) -> str:
        servers = [s.strip() for s in v.split(",") if s.strip()]
        if not servers:
            raise ValueError("kafka_bootstrap_servers must contain at least one broker")
        return ",".join(servers)

    @model_validator(mode="after")
    def _validate_production_secrets(self) -> "Settings":
        """Warn if production is running with default secrets."""
        if self.environment == Environment.PRODUCTION:
            if "CHANGE-ME" in self.secret_key:
                raise ValueError("secret_key must be changed in production")
            if "CHANGE-ME" in self.jwt_secret_key:
                raise ValueError("jwt_secret_key must be changed in production")
        return self

    # -----------------------------------------------------------------------
    # Convenience properties
    # -----------------------------------------------------------------------

    @property
    def is_production(self) -> bool:
        return self.environment == Environment.PRODUCTION

    @property
    def is_development(self) -> bool:
        return self.environment == Environment.DEVELOPMENT

    @property
    def is_testing(self) -> bool:
        return self.environment == Environment.TESTING

    @property
    def kafka_brokers(self) -> list[str]:
        """Kafka brokers as a list."""
        return [s.strip() for s in self.kafka_bootstrap_servers.split(",")]


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return the cached application settings singleton.

    Uses :func:`functools.lru_cache` so the ``.env`` file is only
    parsed once per process.
    """
    return Settings()


__all__ = [
    "Environment",
    "LogLevel",
    "Settings",
    "get_settings",
]
