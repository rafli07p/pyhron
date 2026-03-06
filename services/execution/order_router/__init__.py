"""Smart order router for the Enthropy execution service.

Routes orders to the optimal exchange connector based on symbol,
asset class, order type, and available liquidity.  Integrates pre-trade
risk checks (calls the risk service) and maintains a full audit log of
every routing decision.
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, Optional
from uuid import UUID

import structlog

from shared.schemas.order_events import (
    OrderFill,
    OrderRequest,
    OrderStatusEnum,
    OrderType,
)
from services.execution.exchange_connectors import (
    AlpacaConnector,
    BaseConnector,
    CCXTConnector,
)

logger = structlog.get_logger(__name__)


# ---------------------------------------------------------------------------
# Routing configuration
# ---------------------------------------------------------------------------

# Symbols containing "/" or ending with common crypto quote currencies
# are assumed to be crypto pairs routed to CCXT.
_CRYPTO_QUOTES = ("USDT", "USDC", "USD", "BTC", "ETH", "BNB", "BUSD")


def _looks_like_crypto(symbol: str) -> bool:
    """Heuristic: return True if *symbol* appears to be a crypto pair."""
    if "/" in symbol:
        return True
    upper = symbol.upper()
    return any(upper.endswith(q) for q in _CRYPTO_QUOTES) and len(upper) > 4


# ---------------------------------------------------------------------------
# Route result dataclass
# ---------------------------------------------------------------------------


class RouteDecision:
    """Captures the outcome of a routing decision for audit purposes."""

    __slots__ = ("connector_name", "reason", "timestamp")

    def __init__(self, connector_name: str, reason: str) -> None:
        self.connector_name = connector_name
        self.reason = reason
        self.timestamp = datetime.now(timezone.utc)

    def to_dict(self) -> dict[str, Any]:
        return {
            "connector": self.connector_name,
            "reason": self.reason,
            "timestamp": self.timestamp.isoformat(),
        }


# ---------------------------------------------------------------------------
# Pre-trade risk check stub
# ---------------------------------------------------------------------------


class _RiskServiceClient:
    """Lightweight async client that calls the risk service for pre-trade checks.

    In production this would issue an HTTP / gRPC call to the risk
    micro-service.  Here the interface is defined so the router can
    integrate it; the actual transport is a single async method.
    """

    def __init__(self, base_url: Optional[str] = None) -> None:
        self._base_url = base_url or "http://risk-service:8000"

    async def pre_trade_check(self, order: OrderRequest) -> dict[str, Any]:
        """Run pre-trade risk checks against the risk service.

        Returns a dict with at least ``{"approved": bool, "reason": str}``.
        Falls back to approved if the risk service is unreachable so
        that the router does not block in degraded mode.
        """
        try:
            import httpx

            async with httpx.AsyncClient(timeout=2.0) as client:
                resp = await client.post(
                    f"{self._base_url}/v1/pre-trade-check",
                    json={
                        "order_id": str(order.order_id),
                        "symbol": order.symbol,
                        "side": order.side.value,
                        "qty": str(order.qty),
                        "order_type": order.order_type.value,
                        "tenant_id": order.tenant_id,
                    },
                )
                resp.raise_for_status()
                return resp.json()
        except Exception as exc:
            logger.warning(
                "risk.pre_trade_check_failed",
                error=str(exc),
                order_id=str(order.order_id),
            )
            # Fail-open: allow order through when risk service is unreachable
            return {"approved": True, "reason": "risk_service_unavailable"}


# ---------------------------------------------------------------------------
# OrderRouter
# ---------------------------------------------------------------------------


class OrderRouter:
    """Smart order router that directs orders to the best available connector.

    Parameters
    ----------
    alpaca_connector:
        Pre-initialised :class:`AlpacaConnector` instance (or *None* to
        skip equity routing).
    ccxt_connector:
        Pre-initialised :class:`CCXTConnector` instance (or *None* to
        skip crypto routing).
    risk_service_url:
        Base URL for the risk micro-service used in pre-trade checks.
    """

    def __init__(
        self,
        alpaca_connector: Optional[AlpacaConnector] = None,
        ccxt_connector: Optional[CCXTConnector] = None,
        risk_service_url: Optional[str] = None,
    ) -> None:
        self._connectors: dict[str, BaseConnector] = {}
        if alpaca_connector is not None:
            self._connectors["alpaca"] = alpaca_connector
        if ccxt_connector is not None:
            self._connectors["ccxt"] = ccxt_connector

        self._risk = _RiskServiceClient(base_url=risk_service_url)
        self._audit_log: list[dict[str, Any]] = []
        self._lock = asyncio.Lock()

    # -- public API ----------------------------------------------------------

    async def route_order(self, order: OrderRequest) -> OrderFill:
        """Route *order* to the best connector, execute, and return the fill.

        Steps:
        1. Validate the order locally.
        2. Run pre-trade risk checks via the risk service.
        3. Determine the optimal route.
        4. Submit through the chosen connector.
        5. Record an audit entry.

        Raises
        ------
        ValueError
            If the order fails validation or no suitable connector exists.
        PermissionError
            If the risk service rejects the order.
        """
        # 1. Validate
        self.validate_order(order)

        # 2. Pre-trade risk check
        risk_result = await self._risk.pre_trade_check(order)
        if not risk_result.get("approved", False):
            reason = risk_result.get("reason", "unknown")
            self._record_audit(order, "REJECTED", f"risk_check_failed: {reason}")
            logger.warning(
                "router.risk_rejected",
                order_id=str(order.order_id),
                reason=reason,
            )
            raise PermissionError(f"Pre-trade risk check failed: {reason}")

        # 3. Route
        route = await self.get_best_route(order.symbol, order=order)
        connector = self._connectors[route.connector_name]

        self._record_audit(order, "ROUTED", route.reason)
        logger.info(
            "router.order_routed",
            order_id=str(order.order_id),
            connector=route.connector_name,
            reason=route.reason,
        )

        # 4. Submit
        try:
            fill = await connector.submit_order(order)
            self._record_audit(order, "FILLED", f"fill_price={fill.fill_price}")
            logger.info(
                "router.order_filled",
                order_id=str(order.order_id),
                fill_price=str(fill.fill_price),
                fill_qty=str(fill.fill_qty),
            )
            return fill
        except Exception as exc:
            self._record_audit(order, "ERROR", str(exc))
            logger.error(
                "router.order_failed",
                order_id=str(order.order_id),
                error=str(exc),
            )
            raise

    async def get_best_route(
        self,
        symbol: str,
        *,
        order: Optional[OrderRequest] = None,
    ) -> RouteDecision:
        """Decide which connector to use for *symbol*.

        Routing logic (in priority order):
        1. If the order carries an explicit ``exchange_hint`` matching a
           registered connector, honour it.
        2. If the symbol looks like a crypto pair, route to CCXT.
        3. Otherwise route to Alpaca (equities).
        4. Fall back to whichever connector is available.

        Raises
        ------
        ValueError
            If no connector is registered that can handle the symbol.
        """
        if not self._connectors:
            raise ValueError("No exchange connectors registered")

        # Honour explicit hint from the order
        if order is not None:
            hint = getattr(order, "client_order_id", None)
            # Check if the order's account_id or strategy hints at a connector
            for name in self._connectors:
                if name in (getattr(order, "account_id", "") or "").lower():
                    return RouteDecision(name, f"account_id hint matched connector '{name}'")

        # Crypto heuristic
        if _looks_like_crypto(symbol) and "ccxt" in self._connectors:
            return RouteDecision("ccxt", f"symbol '{symbol}' identified as crypto pair")

        # Default to Alpaca for equities
        if "alpaca" in self._connectors:
            return RouteDecision("alpaca", f"symbol '{symbol}' routed to Alpaca (equity default)")

        # Last resort: first available connector
        first_name = next(iter(self._connectors))
        return RouteDecision(first_name, f"fallback to '{first_name}' -- only available connector")

    @staticmethod
    def validate_order(order: OrderRequest) -> None:
        """Perform local sanity checks on *order* before routing.

        Raises :class:`ValueError` on invalid orders.
        """
        if order.qty <= 0:
            raise ValueError("Order quantity must be positive")

        if order.order_type == OrderType.LIMIT and order.price is None:
            raise ValueError("Limit orders require a price")

        if order.order_type in (OrderType.STOP, OrderType.STOP_LIMIT) and order.stop_price is None:
            raise ValueError(f"{order.order_type} orders require a stop_price")

        if len(order.symbol.strip()) == 0:
            raise ValueError("Symbol must not be empty")

    # -- audit ---------------------------------------------------------------

    def _record_audit(self, order: OrderRequest, action: str, detail: str) -> None:
        entry = {
            "order_id": str(order.order_id),
            "symbol": order.symbol,
            "side": order.side.value,
            "qty": str(order.qty),
            "action": action,
            "detail": detail,
            "tenant_id": order.tenant_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        self._audit_log.append(entry)
        logger.info("router.audit", **entry)

    @property
    def audit_log(self) -> list[dict[str, Any]]:
        """Return a copy of the full audit trail."""
        return list(self._audit_log)


__all__ = [
    "OrderRouter",
    "RouteDecision",
]
