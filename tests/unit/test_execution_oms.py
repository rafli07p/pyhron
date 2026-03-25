"""Unit tests for order execution and OMS components.

Tests the IDX order validator, order timeout monitor logic,
and position reconciliation detection.
"""

from __future__ import annotations

from decimal import Decimal
from unittest.mock import AsyncMock, patch

import pytest

try:
    from data_platform.database_models.order_lifecycle_record import (
        OrderLifecycleRecord,
        OrderSideEnum,
        OrderStatusEnum,
        OrderTypeEnum,
    )
except (ImportError, SyntaxError):
    pytest.skip(
        "Requires Python 3.12+ or database models",
        allow_module_level=True,
    )


# ── IDX Order Validator Tests ───────────────────────────────────────────────


class TestIDXOrderValidator:
    @pytest.fixture(autouse=True)
    def _setup(self) -> None:
        try:
            from services.order_management_system.idx_order_validator import IDXOrderValidator

            self.validator = IDXOrderValidator()
        except (ImportError, SyntaxError):
            pytest.skip("IDXOrderValidator not available")

    def test_valid_lot_size(self) -> None:
        errors = self.validator.validate_quantity(500)  # 5 lots
        assert len(errors) == 0

    def test_invalid_lot_size_not_multiple_of_100(self) -> None:
        errors = self.validator.validate_quantity(150)
        assert any("lot" in e.lower() for e in errors)

    def test_zero_quantity_rejected(self) -> None:
        errors = self.validator.validate_quantity(0)
        assert len(errors) > 0

    def test_negative_quantity_rejected(self) -> None:
        errors = self.validator.validate_quantity(-100)
        assert len(errors) > 0

    def test_valid_tick_size(self) -> None:
        # IDX tick sizes depend on price range
        # Price 200-500: tick = 2
        errors = self.validator.validate_tick_size(Decimal("250"), Decimal("252"))
        assert len(errors) == 0

    def test_valid_symbol_format(self) -> None:
        errors = self.validator.validate_symbol("BBCA")
        assert len(errors) == 0

    def test_empty_symbol_rejected(self) -> None:
        errors = self.validator.validate_symbol("")
        assert len(errors) > 0


# ── Order Lifecycle Record Tests ────────────────────────────────────────────


class TestOrderLifecycleRecord:
    def test_order_model_fields(self) -> None:
        """Verify the ORM model has all expected columns."""
        columns = {c.name for c in OrderLifecycleRecord.__table__.columns}
        expected = {
            "client_order_id",
            "broker_order_id",
            "user_id",
            "strategy_id",
            "symbol",
            "exchange",
            "side",
            "order_type",
            "quantity",
            "filled_quantity",
            "limit_price",
            "stop_price",
            "avg_fill_price",
            "status",
            "currency",
            "time_in_force",
            "commission",
            "tax",
            "rejection_reason",
            "signal_time",
            "submitted_at",
            "acknowledged_at",
            "filled_at",
            "created_at",
            "updated_at",
        }
        assert expected.issubset(columns)

    def test_order_status_enum_values(self) -> None:
        assert OrderStatusEnum.PENDING_RISK.value == "pending_risk"
        assert OrderStatusEnum.FILLED.value == "filled"
        assert OrderStatusEnum.CANCELLED.value == "cancelled"

    def test_order_side_enum_values(self) -> None:
        assert OrderSideEnum.BUY.value == "buy"
        assert OrderSideEnum.SELL.value == "sell"

    def test_order_type_enum_values(self) -> None:
        assert OrderTypeEnum.MARKET.value == "market"
        assert OrderTypeEnum.LIMIT.value == "limit"
        assert OrderTypeEnum.STOP.value == "stop"
        assert OrderTypeEnum.STOP_LIMIT.value == "stop_limit"

    def test_check_constraint_exists(self) -> None:
        """Verify filled_quantity <= quantity constraint is defined."""
        constraints = [c.name for c in OrderLifecycleRecord.__table__.constraints if hasattr(c, "name")]
        assert any("filled_lte_quantity" in (n or "") for n in constraints)

    def test_indexes_defined(self) -> None:
        index_names = {idx.name for idx in OrderLifecycleRecord.__table__.indexes}
        assert "ix_order_lifecycle_records_strategy_created" in index_names
        assert "ix_order_lifecycle_records_symbol_status" in index_names
        assert "ix_order_lifecycle_records_broker_id" in index_names


# ── Circuit Breaker State Manager Tests ─────────────────────────────────────


class TestCircuitBreakerStateManager:
    @pytest.fixture()
    def manager(self):
        from services.pre_trade_risk_engine.circuit_breaker_state_manager import (
            CircuitBreakerStateManager,
        )

        return CircuitBreakerStateManager(default_ttl_seconds=300)

    @pytest.mark.asyncio()
    async def test_halt_sets_redis_key(self, manager) -> None:
        from services.pre_trade_risk_engine.circuit_breaker_state_manager import (
            CircuitBreakerReason,
        )

        mock_redis = AsyncMock()
        mock_redis.set = AsyncMock()
        mock_redis.lpush = AsyncMock()
        mock_redis.ltrim = AsyncMock()

        with patch("services.pre_trade_risk_engine.circuit_breaker_state_manager.get_redis", return_value=mock_redis):
            state = await manager.halt(
                entity_id="strat-001",
                reason=CircuitBreakerReason.DAILY_LOSS_LIMIT,
                detail="Lost 3% today",
            )

        assert state.is_active
        assert state.reason == CircuitBreakerReason.DAILY_LOSS_LIMIT
        assert state.entity_id == "strat-001"
        mock_redis.set.assert_called_once()

    @pytest.mark.asyncio()
    async def test_resume_deletes_redis_key(self, manager) -> None:
        mock_redis = AsyncMock()
        mock_redis.delete = AsyncMock(return_value=1)
        mock_redis.lpush = AsyncMock()
        mock_redis.ltrim = AsyncMock()

        with patch("services.pre_trade_risk_engine.circuit_breaker_state_manager.get_redis", return_value=mock_redis):
            cleared = await manager.resume("strat-001", reason="manual clear")

        assert cleared is True
        mock_redis.delete.assert_called_once()

    @pytest.mark.asyncio()
    async def test_resume_returns_false_if_not_active(self, manager) -> None:
        mock_redis = AsyncMock()
        mock_redis.delete = AsyncMock(return_value=0)
        mock_redis.lpush = AsyncMock()
        mock_redis.ltrim = AsyncMock()

        with patch("services.pre_trade_risk_engine.circuit_breaker_state_manager.get_redis", return_value=mock_redis):
            cleared = await manager.resume("strat-nonexistent")

        assert cleared is False

    @pytest.mark.asyncio()
    async def test_is_halted_checks_redis(self, manager) -> None:
        mock_redis = AsyncMock()
        mock_redis.get = AsyncMock(return_value="DAILY_LOSS_LIMIT:detail:2024-01-01T00:00:00")

        with patch("services.pre_trade_risk_engine.circuit_breaker_state_manager.get_redis", return_value=mock_redis):
            halted = await manager.is_halted("strat-001")

        assert halted is True

    @pytest.mark.asyncio()
    async def test_get_state_inactive(self, manager) -> None:
        mock_redis = AsyncMock()
        mock_redis.get = AsyncMock(return_value=None)

        with patch("services.pre_trade_risk_engine.circuit_breaker_state_manager.get_redis", return_value=mock_redis):
            state = await manager.get_state("strat-001")

        assert state.is_active is False
        assert state.reason is None

    @pytest.mark.asyncio()
    async def test_get_state_active_parses_value(self, manager) -> None:
        mock_redis = AsyncMock()
        mock_redis.get = AsyncMock(return_value="VAR_BREACH:VaR exceeded 95th pctl:2024-01-15T10:30:00+00:00")
        mock_redis.ttl = AsyncMock(return_value=250)

        with patch("services.pre_trade_risk_engine.circuit_breaker_state_manager.get_redis", return_value=mock_redis):
            state = await manager.get_state("strat-001")

        assert state.is_active is True
        assert state.reason is not None
        assert state.ttl_seconds == 250


# ── Position Snapshot Tests ─────────────────────────────────────────────────


class TestStrategyPositionSnapshot:
    def test_position_model_fields(self) -> None:
        from data_platform.database_models.strategy_position_snapshot import StrategyPositionSnapshot

        columns = {c.name for c in StrategyPositionSnapshot.__table__.columns}
        expected = {
            "id",
            "strategy_id",
            "symbol",
            "exchange",
            "quantity",
            "avg_entry_price",
            "current_price",
            "unrealized_pnl",
            "realized_pnl",
            "market_value",
            "last_updated",
        }
        assert expected.issubset(columns)

    def test_unique_constraint(self) -> None:
        from data_platform.database_models.strategy_position_snapshot import StrategyPositionSnapshot

        constraints = StrategyPositionSnapshot.__table__.constraints
        unique_names = [c.name for c in constraints if hasattr(c, "columns") and len(c.columns) > 1]
        # Should have a unique constraint on (strategy_id, symbol, exchange)
        assert len(unique_names) > 0

    def test_check_constraint_quantity_non_negative(self) -> None:
        from data_platform.database_models.strategy_position_snapshot import StrategyPositionSnapshot

        constraint_names = [c.name for c in StrategyPositionSnapshot.__table__.constraints if hasattr(c, "name")]
        assert any("quantity_non_negative" in (n or "") for n in constraint_names)
