"""Unit tests for the order timeout monitor.

Validates TTL configuration, expirable statuses, and the timeout
calculation logic.
"""

from __future__ import annotations

import pytest

try:
    from data_platform.database_models.order_lifecycle_record import OrderStatusEnum
    from services.order_management_system.order_timeout_monitor import (
        DEFAULT_LIMIT_ORDER_TTL_SECONDS,
        DEFAULT_ORDER_TTL_SECONDS,
        DEFAULT_SCAN_INTERVAL_SECONDS,
        EXPIRABLE_STATUSES,
    )
except ImportError:
    pytest.skip("Requires OMS modules", allow_module_level=True)


class TestTimeoutConfiguration:
    """Tests for timeout configuration constants."""

    def test_scan_interval_reasonable(self) -> None:
        """Scan interval should be between 10s and 300s."""
        assert 10 <= DEFAULT_SCAN_INTERVAL_SECONDS <= 300

    def test_market_order_ttl(self) -> None:
        """Market order TTL should be 5 minutes (300s)."""
        assert DEFAULT_ORDER_TTL_SECONDS == 300

    def test_limit_order_ttl(self) -> None:
        """Limit order TTL should be 8 hours (28800s)."""
        assert DEFAULT_LIMIT_ORDER_TTL_SECONDS == 28800

    def test_limit_ttl_longer_than_market(self) -> None:
        """Limit order TTL should be longer than market order TTL."""
        assert DEFAULT_LIMIT_ORDER_TTL_SECONDS > DEFAULT_ORDER_TTL_SECONDS


class TestExpirableStatuses:
    """Tests for which statuses can be expired."""

    def test_submitted_is_expirable(self) -> None:
        """SUBMITTED orders can be expired."""
        assert OrderStatusEnum.SUBMITTED in EXPIRABLE_STATUSES

    def test_acknowledged_is_expirable(self) -> None:
        """ACKNOWLEDGED orders can be expired."""
        assert OrderStatusEnum.ACKNOWLEDGED in EXPIRABLE_STATUSES

    def test_filled_is_not_expirable(self) -> None:
        """FILLED orders should not be expired."""
        assert OrderStatusEnum.FILLED not in EXPIRABLE_STATUSES

    def test_cancelled_is_not_expirable(self) -> None:
        """Already CANCELLED orders should not be expired."""
        assert OrderStatusEnum.CANCELLED not in EXPIRABLE_STATUSES

    def test_pending_risk_not_expirable(self) -> None:
        """PENDING_RISK orders should not be directly expired."""
        assert OrderStatusEnum.PENDING_RISK not in EXPIRABLE_STATUSES

    def test_only_two_expirable_statuses(self) -> None:
        """Exactly SUBMITTED and ACKNOWLEDGED should be expirable."""
        assert len(EXPIRABLE_STATUSES) == 2
