"""Unit tests for shared.configuration_settings — Config validators."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from shared.configuration_settings import Config


class TestCORSValidator:
    def test_wildcard_rejected_in_production(self) -> None:
        with pytest.raises(ValidationError, match="allowed_cors_origins"):
            Config(
                app_env="production",
                allowed_cors_origins="*",
                app_secret_key="prod-secret-key-that-is-long-enough-32",
                jwt_secret_key="prod-jwt-secret-key-that-is-definitely-long-enough-64-chars-here",
            )

    def test_wildcard_allowed_in_development(self) -> None:
        cfg = Config(app_env="development", allowed_cors_origins="*")
        assert cfg.allowed_cors_origins == "*"

    def test_specific_origins_in_production(self) -> None:
        cfg = Config(
            app_env="production",
            allowed_cors_origins="https://app.pyhron.io,https://admin.pyhron.io",
            app_secret_key="prod-secret-key-that-is-long-enough-32",
            jwt_secret_key="prod-jwt-secret-key-that-is-definitely-long-enough-64-chars-here",
        )
        assert "app.pyhron.io" in cfg.allowed_cors_origins


class TestSecretValidators:
    def test_default_app_secret_rejected_in_production(self) -> None:
        with pytest.raises(ValidationError, match="app_secret_key"):
            Config(
                app_env="production",
                app_secret_key="local-dev-secret-key-min-32-chars-long",
                jwt_secret_key="prod-jwt-secret-key-that-is-definitely-long-enough-64-chars-here",
            )

    def test_default_jwt_secret_rejected_in_production(self) -> None:
        with pytest.raises(ValidationError, match="jwt_secret_key"):
            Config(
                app_env="production",
                app_secret_key="prod-secret-key-that-is-long-enough-32",
                jwt_secret_key="local-dev-jwt-secret-change-in-prod-min-64",
            )


class TestDatabaseURLValidator:
    def test_postgresql_url_accepted(self) -> None:
        cfg = Config(database_url="postgresql+asyncpg://u:p@localhost/db")
        assert cfg.database_url.startswith("postgresql")

    def test_sqlite_url_accepted(self) -> None:
        cfg = Config(database_url="sqlite:///test.db")
        assert cfg.database_url.startswith("sqlite")

    def test_invalid_url_rejected(self) -> None:
        with pytest.raises(ValidationError, match="database_url"):
            Config(database_url="mysql://u:p@localhost/db")


class TestKafkaValidator:
    def test_valid_kafka_servers(self) -> None:
        cfg = Config(kafka_bootstrap_servers="broker1:9092,broker2:9092")
        assert cfg.kafka_brokers == ["broker1:9092", "broker2:9092"]

    def test_empty_kafka_servers_rejected(self) -> None:
        with pytest.raises(ValidationError, match="kafka_bootstrap_servers"):
            Config(kafka_bootstrap_servers="")


class TestProperties:
    def test_is_production(self) -> None:
        cfg = Config(app_env="production",
                     app_secret_key="prod-secret-key-that-is-long-enough-32",
                     jwt_secret_key="prod-jwt-secret-key-that-is-definitely-long-enough-64-chars-here",
                     allowed_cors_origins="https://app.pyhron.io")
        assert cfg.is_production is True
        assert cfg.is_development is False

    def test_is_development(self) -> None:
        cfg = Config(app_env="development")
        assert cfg.is_development is True
        assert cfg.is_production is False
