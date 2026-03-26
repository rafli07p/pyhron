"""Unit tests for the smart order router.

Validates routing logic, order validation, pre-trade risk integration,
crypto heuristics, and audit trail recording.
"""

from __future__ import annotations

from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

try:
    from services.execution.exchange_connectors import BaseConnector
    from services.execution.order_router import OrderRouter, RouteDecision, _looks_like_crypto
    from shared.schemas.order_events import (
        OrderFill,
        OrderRequest,
        OrderSide,
        OrderStatusEnum,
        OrderType,
    )
except ImportError:
    pytest.skip("Requires execution modules", allow_module_level=True)


def _make_order(
    symbol: str = "BBCA.JK",
    side: OrderSide = OrderSide.BUY,
    qty: Decimal = Decimal("100"),
    price: Decimal | None = Decimal("9200"),
    order_type: OrderType = OrderType.LIMIT,
    account_id: str | None = None,
) -> OrderRequest:
    return OrderRequest(
        order_id=uuid4(),
        symbol=symbol,
        side=side,
        qty=qty,
        price=price,
        order_type=order_type,
        tenant_id="test-tenant",
        account_id=account_id,
    )


def _make_fill(order: OrderRequest) -> OrderFill:
    return OrderFill(
        fill_id=uuid4(),
        order_id=order.order_id,
        symbol=order.symbol,
        side=order.side,
        qty=order.qty,
        price=order.price or Decimal("9200"),
        order_type=order.order_type,
        tenant_id=order.tenant_id,
        fill_qty=order.qty,
        fill_price=order.price or Decimal("9200"),
        cumulative_qty=order.qty,
        leaves_qty=Decimal("0"),
        status=OrderStatusEnum.FILLED,
        exchange="TEST",
    )


def _make_mock_connector(name: str = "alpaca") -> MagicMock:
    connector = MagicMock(spec=BaseConnector)
    connector.name = name
    connector.connected = True
    return connector


class TestCryptoHeuristic:
    """Tests for the crypto symbol detection heuristic."""

    @pytest.mark.parametrize(
        "symbol,expected",
        [
            ("BTC/USDT", True),
            ("ETH/BTC", True),
            ("BTCUSDT", True),
            ("ETHBTC", True),
            ("SOLUSDC", True),
            ("BBCA.JK", False),
            ("AAPL", False),
            ("TLKM", False),
            ("BTC", False),  # too short
        ],
    )
    def test_crypto_detection(self, symbol: str, expected: bool) -> None:
        """Should correctly identify crypto vs equity symbols."""
        assert _looks_like_crypto(symbol) is expected


class TestOrderValidation:
    """Tests for local order validation."""

    def test_valid_limit_order_passes(self) -> None:
        """Valid limit order should not raise."""
        order = _make_order(order_type=OrderType.LIMIT, price=Decimal("9200"))
        OrderRouter.validate_order(order)

    def test_zero_quantity_rejected(self) -> None:
        """Zero quantity order should raise ValueError from Pydantic."""
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            _make_order(qty=Decimal("0"))

    def test_limit_order_without_price_rejected(self) -> None:
        """Limit order without price should raise ValueError."""
        # Pydantic model_validator catches this, but let's verify the static method
        order = _make_order(order_type=OrderType.MARKET, price=None)
        # Manually set order_type to LIMIT to bypass Pydantic
        object.__setattr__(order, "order_type", OrderType.LIMIT)
        with pytest.raises(ValueError, match="price"):
            OrderRouter.validate_order(order)

    def test_empty_symbol_rejected(self) -> None:
        """Empty symbol should raise ValueError."""
        order = _make_order()
        object.__setattr__(order, "symbol", "   ")
        with pytest.raises(ValueError, match="empty"):
            OrderRouter.validate_order(order)


class TestRouteDecision:
    """Tests for routing decisions."""

    @pytest.mark.asyncio
    async def test_equity_routes_to_alpaca(self) -> None:
        """Equity symbol should route to Alpaca connector."""
        alpaca = _make_mock_connector("alpaca")
        router = OrderRouter(alpaca_connector=alpaca)

        decision = await router.get_best_route("BBCA.JK")
        assert decision.connector_name == "alpaca"

    @pytest.mark.asyncio
    async def test_crypto_routes_to_ccxt(self) -> None:
        """Crypto symbol should route to CCXT connector."""
        alpaca = _make_mock_connector("alpaca")
        ccxt = _make_mock_connector("ccxt")
        router = OrderRouter(alpaca_connector=alpaca, ccxt_connector=ccxt)

        decision = await router.get_best_route("BTC/USDT")
        assert decision.connector_name == "ccxt"

    @pytest.mark.asyncio
    async def test_account_hint_overrides_heuristic(self) -> None:
        """Account ID matching connector name should override heuristic."""
        alpaca = _make_mock_connector("alpaca")
        ccxt = _make_mock_connector("ccxt")
        router = OrderRouter(alpaca_connector=alpaca, ccxt_connector=ccxt)

        order = _make_order(symbol="BBCA.JK", account_id="ccxt-main")
        decision = await router.get_best_route("BBCA.JK", order=order)
        assert decision.connector_name == "ccxt"

    @pytest.mark.asyncio
    async def test_fallback_to_only_connector(self) -> None:
        """Should fall back to the only available connector."""
        ccxt = _make_mock_connector("ccxt")
        router = OrderRouter(ccxt_connector=ccxt)

        decision = await router.get_best_route("BBCA.JK")
        assert decision.connector_name == "ccxt"
        assert "fallback" in decision.reason or "only" in decision.reason

    @pytest.mark.asyncio
    async def test_no_connectors_raises(self) -> None:
        """Should raise ValueError when no connectors registered."""
        router = OrderRouter()
        with pytest.raises(ValueError, match="No exchange connectors"):
            await router.get_best_route("BBCA.JK")

    def test_route_decision_to_dict(self) -> None:
        """RouteDecision should serialize to dict."""
        decision = RouteDecision("alpaca", "equity default")
        d = decision.to_dict()
        assert d["connector"] == "alpaca"
        assert d["reason"] == "equity default"
        assert "timestamp" in d


class TestOrderRouterExecution:
    """Tests for the full route_order pipeline."""

    @pytest.mark.asyncio
    async def test_successful_order_routing(self) -> None:
        """Order should be routed, executed, and audited."""
        alpaca = _make_mock_connector("alpaca")
        order = _make_order()
        fill = _make_fill(order)
        alpaca.submit_order = AsyncMock(return_value=fill)

        router = OrderRouter(alpaca_connector=alpaca)

        with patch.object(router._risk, "pre_trade_check", return_value={"approved": True}):
            result = await router.route_order(order)

        assert result.fill_price == Decimal("9200")
        assert len(router.audit_log) >= 2  # ROUTED + FILLED

    @pytest.mark.asyncio
    async def test_risk_rejection_raises_permission_error(self) -> None:
        """Risk check failure should raise PermissionError."""
        alpaca = _make_mock_connector("alpaca")
        router = OrderRouter(alpaca_connector=alpaca)

        with patch.object(
            router._risk,
            "pre_trade_check",
            return_value={"approved": False, "reason": "var_limit_exceeded"},
        ):
            with pytest.raises(PermissionError, match="risk"):
                await router.route_order(_make_order())

        assert any("REJECTED" in entry["action"] for entry in router.audit_log)

    @pytest.mark.asyncio
    async def test_connector_failure_records_error(self) -> None:
        """Connector failure should be recorded in audit log."""
        alpaca = _make_mock_connector("alpaca")
        alpaca.submit_order = AsyncMock(side_effect=ConnectionError("exchange down"))

        router = OrderRouter(alpaca_connector=alpaca)

        with patch.object(router._risk, "pre_trade_check", return_value={"approved": True}):
            with pytest.raises(ConnectionError):
                await router.route_order(_make_order())

        assert any("ERROR" in entry["action"] for entry in router.audit_log)

    @pytest.mark.asyncio
    async def test_audit_log_is_copy(self) -> None:
        """audit_log should return a copy, not the internal list."""
        router = OrderRouter()
        log1 = router.audit_log
        log2 = router.audit_log
        assert log1 is not log2
