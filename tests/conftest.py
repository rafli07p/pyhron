"""
Shared pytest fixtures for the Enthropy test suite.

Provides mock settings, sample data objects, database sessions,
and common test utilities used across unit, integration, and e2e tests.
"""

from __future__ import annotations

import asyncio
import os
from datetime import datetime, timezone
from decimal import Decimal
from typing import AsyncGenerator, Generator
from uuid import uuid4

import pytest
import pytest_asyncio

from enthropy.shared.schemas.order import (
    OrderCreate,
    OrderResponse,
    OrderSide,
    OrderStatus,
    OrderType,
)
from enthropy.shared.schemas.tick import TickData
from enthropy.shared.schemas.position import PositionSnapshot
from enthropy.shared.schemas.risk import RiskLimits


# =============================================================================
# Event Loop Configuration
# =============================================================================
@pytest.fixture(scope="session")
def event_loop():
    """Create a single event loop for the entire test session."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


# =============================================================================
# Settings Fixtures
# =============================================================================
@pytest.fixture
def mock_settings() -> dict:
    """Mock application settings for testing.

    Returns a dictionary of settings that mirror the production
    configuration but with test-appropriate values.
    """
    return {
        "environment": "test",
        "debug": True,
        "log_level": "DEBUG",
        # Database
        "database_url": os.environ.get(
            "DATABASE_URL",
            "postgresql+asyncpg://enthropy:enthropy_test@localhost:5432/enthropy_test",
        ),
        "database_pool_size": 5,
        "database_max_overflow": 2,
        "database_pool_timeout": 10,
        # Redis
        "redis_url": os.environ.get("REDIS_URL", "redis://localhost:6379/1"),
        "redis_max_connections": 10,
        # Kafka
        "kafka_bootstrap_servers": os.environ.get(
            "KAFKA_BOOTSTRAP_SERVERS", "localhost:9092"
        ),
        "kafka_consumer_group": "enthropy-test",
        # API
        "api_host": "0.0.0.0",
        "api_port": 8000,
        "api_key": "test-api-key-not-for-production",
        "cors_origins": ["http://localhost:3000"],
        # Encryption
        "encryption_key": "dGVzdC1lbmNyeXB0aW9uLWtleS0yNTYtYml0cyE=",
        # Market Data
        "market_data_api_key": os.environ.get("MARKET_DATA_API_KEY", ""),
        "market_data_base_url": "https://api.marketdata.example.com",
        # Risk
        "max_position_size": Decimal("10000000.00"),
        "max_order_size": Decimal("1000000.00"),
        "max_daily_loss": Decimal("500000.00"),
        "max_drawdown_pct": Decimal("0.10"),
        # MLflow
        "mlflow_tracking_uri": "http://localhost:5000",
    }


# =============================================================================
# Order Fixtures
# =============================================================================
@pytest.fixture
def sample_order() -> OrderCreate:
    """Sample buy limit order for BBCA.JK.

    Represents a typical institutional order on the Indonesian
    Stock Exchange (IDX) with standard lot sizing.
    """
    return OrderCreate(
        symbol="BBCA.JK",
        side=OrderSide.BUY,
        order_type=OrderType.LIMIT,
        quantity=Decimal("1000"),
        price=Decimal("9200.00"),
        strategy_id="test_strategy_v1",
    )


@pytest.fixture
def sample_market_order() -> OrderCreate:
    """Sample market sell order."""
    return OrderCreate(
        symbol="TLKM.JK",
        side=OrderSide.SELL,
        order_type=OrderType.MARKET,
        quantity=Decimal("500"),
        price=None,
        strategy_id="test_strategy_v1",
    )


@pytest.fixture
def sample_order_response() -> OrderResponse:
    """Sample order response with a filled status."""
    return OrderResponse(
        order_id=uuid4(),
        symbol="BBCA.JK",
        side=OrderSide.BUY,
        order_type=OrderType.LIMIT,
        quantity=Decimal("1000"),
        filled_quantity=Decimal("1000"),
        price=Decimal("9200.00"),
        average_fill_price=Decimal("9205.50"),
        status=OrderStatus.FILLED,
        strategy_id="test_strategy_v1",
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )


# =============================================================================
# Market Data Fixtures
# =============================================================================
@pytest.fixture
def sample_tick() -> TickData:
    """Sample tick data for BBCA.JK.

    Represents a single market data update with bid/ask spread
    typical for a liquid IDX blue chip.
    """
    return TickData(
        symbol="BBCA.JK",
        price=Decimal("9250.00"),
        volume=1_500_000,
        bid=Decimal("9245.00"),
        ask=Decimal("9255.00"),
        timestamp=datetime.now(timezone.utc),
        exchange="IDX",
    )


@pytest.fixture
def sample_ticks() -> list[TickData]:
    """Multiple tick data samples across different symbols."""
    now = datetime.now(timezone.utc)
    return [
        TickData(
            symbol="BBCA.JK",
            price=Decimal("9250.00"),
            volume=1_500_000,
            bid=Decimal("9245.00"),
            ask=Decimal("9255.00"),
            timestamp=now,
            exchange="IDX",
        ),
        TickData(
            symbol="TLKM.JK",
            price=Decimal("3850.00"),
            volume=3_200_000,
            bid=Decimal("3845.00"),
            ask=Decimal("3855.00"),
            timestamp=now,
            exchange="IDX",
        ),
        TickData(
            symbol="BMRI.JK",
            price=Decimal("6200.00"),
            volume=800_000,
            bid=Decimal("6195.00"),
            ask=Decimal("6205.00"),
            timestamp=now,
            exchange="IDX",
        ),
        TickData(
            symbol="BBRI.JK",
            price=Decimal("4525.00"),
            volume=5_000_000,
            bid=Decimal("4520.00"),
            ask=Decimal("4530.00"),
            timestamp=now,
            exchange="IDX",
        ),
    ]


# =============================================================================
# Position Fixtures
# =============================================================================
@pytest.fixture
def sample_position() -> PositionSnapshot:
    """Sample long position in BBCA.JK."""
    return PositionSnapshot(
        symbol="BBCA.JK",
        quantity=Decimal("5000"),
        average_entry_price=Decimal("9100.00"),
        current_price=Decimal("9250.00"),
        unrealized_pnl=Decimal("750000.00"),
        realized_pnl=Decimal("200000.00"),
        market_value=Decimal("46250000.00"),
        strategy_id="momentum_v1",
        updated_at=datetime.now(timezone.utc),
    )


@pytest.fixture
def sample_portfolio() -> list[PositionSnapshot]:
    """Sample portfolio with multiple positions."""
    now = datetime.now(timezone.utc)
    return [
        PositionSnapshot(
            symbol="BBCA.JK",
            quantity=Decimal("5000"),
            average_entry_price=Decimal("9100.00"),
            current_price=Decimal("9250.00"),
            unrealized_pnl=Decimal("750000.00"),
            realized_pnl=Decimal("200000.00"),
            market_value=Decimal("46250000.00"),
            strategy_id="momentum_v1",
            updated_at=now,
        ),
        PositionSnapshot(
            symbol="TLKM.JK",
            quantity=Decimal("10000"),
            average_entry_price=Decimal("3800.00"),
            current_price=Decimal("3850.00"),
            unrealized_pnl=Decimal("500000.00"),
            realized_pnl=Decimal("150000.00"),
            market_value=Decimal("38500000.00"),
            strategy_id="value_v1",
            updated_at=now,
        ),
        PositionSnapshot(
            symbol="BMRI.JK",
            quantity=Decimal("-2000"),
            average_entry_price=Decimal("6300.00"),
            current_price=Decimal("6200.00"),
            unrealized_pnl=Decimal("200000.00"),
            realized_pnl=Decimal("0.00"),
            market_value=Decimal("-12400000.00"),
            strategy_id="pairs_v1",
            updated_at=now,
        ),
    ]


# =============================================================================
# Risk Fixtures
# =============================================================================
@pytest.fixture
def sample_risk_limits() -> RiskLimits:
    """Standard risk limits for testing."""
    return RiskLimits(
        max_position_size=Decimal("10000000.00"),
        max_order_size=Decimal("1000000.00"),
        max_daily_loss=Decimal("500000.00"),
        max_drawdown_pct=Decimal("0.10"),
        max_var=Decimal("2000000.00"),
        max_concentration_pct=Decimal("0.25"),
        max_leverage=Decimal("2.0"),
    )


# =============================================================================
# Database Fixtures
# =============================================================================
@pytest_asyncio.fixture
async def db_session(mock_settings: dict) -> AsyncGenerator:
    """Async database session for integration tests.

    Creates a fresh transaction for each test and rolls back
    after the test completes, ensuring test isolation.
    """
    from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
    from sqlalchemy.orm import sessionmaker

    engine = create_async_engine(
        mock_settings["database_url"],
        echo=mock_settings.get("debug", False),
        pool_size=mock_settings["database_pool_size"],
        max_overflow=mock_settings["database_max_overflow"],
        pool_timeout=mock_settings["database_pool_timeout"],
    )

    async_session = sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )

    async with async_session() as session:
        async with session.begin():
            yield session
            # Rollback after each test for isolation
            await session.rollback()

    await engine.dispose()


# =============================================================================
# Utility Fixtures
# =============================================================================
@pytest.fixture
def generate_order_id():
    """Factory fixture to generate unique order IDs."""
    def _generate():
        return uuid4()
    return _generate


@pytest.fixture
def assert_decimal_close():
    """Helper to assert two Decimals are close within tolerance."""
    def _assert(actual: Decimal, expected: Decimal, tolerance: Decimal = Decimal("0.01")):
        diff = abs(actual - expected)
        assert diff <= tolerance, (
            f"Decimal values not close enough: {actual} vs {expected} "
            f"(diff={diff}, tolerance={tolerance})"
        )
    return _assert


# =============================================================================
# Pytest Configuration
# =============================================================================
def pytest_configure(config):
    """Register custom markers."""
    config.addinivalue_line(
        "markers", "slow: marks tests as slow (deselect with '-m \"not slow\"')"
    )
    config.addinivalue_line(
        "markers", "integration: marks integration tests requiring external services"
    )
    config.addinivalue_line(
        "markers", "e2e: marks end-to-end tests"
    )
    config.addinivalue_line(
        "markers", "benchmark: marks performance benchmark tests"
    )
