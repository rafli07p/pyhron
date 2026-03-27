"""Pre-trade validation for the Pyhron trading platform.

Runs margin checks, position-limit validation, restricted-list
screening, and wash-trade detection before an order is sent to
the execution layer.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Any

import structlog

from shared.schemas.order_events import OrderFill, OrderRequest, OrderSide

logger = structlog.get_logger(__name__)


# Result types

@dataclass(frozen=True)
class CheckResult:
    """Outcome of a pre-trade validation."""

    approved: bool
    reason: str
    check_name: str = ""
    details: dict[str, Any] = field(default_factory=dict)


# Configuration

@dataclass
class PreTradeConfig:
    """Per-tenant pre-trade check configuration."""

    # Margin
    initial_margin_pct: float = 50.0  # Reg-T default
    maintenance_margin_pct: float = 25.0
    margin_buffer_pct: float = 5.0  # extra buffer

    # Position limits
    max_position_qty: Decimal = Decimal("100000")
    max_position_value: Decimal = Decimal("10000000")

    # Restricted list
    restricted_symbols: list[str] = field(default_factory=list)

    # Wash-trade window
    wash_trade_window_seconds: int = 60


_DEFAULT_CONFIG = PreTradeConfig()


# Service

class PreTradeCheckService:
    """Runs a battery of pre-trade checks on incoming orders.

    Each check is executed sequentially; the first failure short-circuits
    the validation and returns a rejected ``CheckResult``.

    Parameters
    ----------
    tenant_configs:
        Per-tenant configuration.  Tenants without an entry get defaults.
    """

    def __init__(
        self,
        tenant_configs: dict[str, PreTradeConfig] | None = None,
    ) -> None:
        self._configs = tenant_configs or {}
        self._log = logger.bind(component="PreTradeCheckService")

        # Recent order cache for wash-trade detection
        # Key: (tenant_id, symbol), Value: list of (timestamp, side, qty)
        self._recent_orders: dict[
            tuple[str, str], list[tuple[datetime, str, Decimal]]
        ] = {}

    def _cfg(self, tenant_id: str) -> PreTradeConfig:
        return self._configs.get(tenant_id, _DEFAULT_CONFIG)

    # Public API

    async def validate_order(
        self,
        order: OrderRequest,
        account_equity: Decimal | None = None,
        current_position_qty: Decimal = Decimal("0"),
        current_position_value: Decimal = Decimal("0"),
        current_margin_used: Decimal = Decimal("0"),
    ) -> CheckResult:
        """Run all pre-trade checks and return the aggregate result.

        Parameters
        ----------
        order:
            The incoming order request.
        account_equity:
            Account equity for margin calculations.
        current_position_qty:
            Current position quantity in this symbol.
        current_position_value:
            Current market value of the position.
        current_margin_used:
            Total margin already in use.

        Returns
        -------
        CheckResult
            ``approved=True`` if all checks pass, else the first
            failing check's reason.
        """
        self._log.info(
            "validate_order",
            tenant_id=order.tenant_id,
            symbol=order.symbol,
            side=order.side,
            qty=str(order.qty),
        )

        checks = [
            self._check_restricted_list(order),
            self._check_position_limit(order, current_position_qty, current_position_value),
            self._check_margin(order, account_equity, current_margin_used),
            self._check_wash_trade(order),
        ]

        for check in checks:
            if not check.approved:
                self._log.warning(
                    "pre_trade_rejected",
                    tenant_id=order.tenant_id,
                    symbol=order.symbol,
                    check=check.check_name,
                    reason=check.reason,
                )
                return check

        # Record this order for wash-trade tracking
        self._record_order(order)

        return CheckResult(
            approved=True,
            reason="All pre-trade checks passed",
            check_name="all",
        )

    # Individual checks

    def _check_restricted_list(self, order: OrderRequest) -> CheckResult:
        """Reject orders for symbols on the restricted list."""
        cfg = self._cfg(order.tenant_id)
        if order.symbol in cfg.restricted_symbols:
            return CheckResult(
                approved=False,
                reason=f"Symbol {order.symbol} is on the restricted trading list",
                check_name="restricted_list",
                details={"symbol": order.symbol},
            )
        return CheckResult(approved=True, reason="", check_name="restricted_list")

    def _check_position_limit(
        self,
        order: OrderRequest,
        current_qty: Decimal,
        current_value: Decimal,
    ) -> CheckResult:
        """Ensure the post-trade position stays within limits."""
        cfg = self._cfg(order.tenant_id)

        signed_order_qty = order.qty if order.side == OrderSide.BUY else -order.qty
        projected_qty = current_qty + signed_order_qty

        if abs(projected_qty) > cfg.max_position_qty:
            return CheckResult(
                approved=False,
                reason=(
                    f"Projected position {projected_qty} exceeds limit "
                    f"{cfg.max_position_qty} for {order.symbol}"
                ),
                check_name="position_limit",
                details={
                    "projected_qty": str(projected_qty),
                    "limit": str(cfg.max_position_qty),
                },
            )

        # Estimate projected value
        order_price = order.price if order.price is not None else Decimal("0")
        projected_value = current_value + (signed_order_qty * order_price)
        if abs(projected_value) > cfg.max_position_value:
            return CheckResult(
                approved=False,
                reason=(
                    f"Projected position value {projected_value} exceeds limit "
                    f"{cfg.max_position_value} for {order.symbol}"
                ),
                check_name="position_limit",
                details={
                    "projected_value": str(projected_value),
                    "limit": str(cfg.max_position_value),
                },
            )

        return CheckResult(approved=True, reason="", check_name="position_limit")

    def _check_margin(
        self,
        order: OrderRequest,
        account_equity: Decimal | None,
        current_margin_used: Decimal,
    ) -> CheckResult:
        """Verify sufficient margin for the proposed order."""
        if account_equity is None:
            # Cannot check margin without account equity; pass through
            return CheckResult(
                approved=True,
                reason="Margin check skipped (no equity provided)",
                check_name="margin",
            )

        cfg = self._cfg(order.tenant_id)
        order_price = order.price if order.price is not None else Decimal("0")
        order_notional = order.qty * order_price
        margin_required = order_notional * Decimal(str(cfg.initial_margin_pct / 100))

        available_margin = account_equity - current_margin_used
        margin_with_buffer = margin_required * (1 + Decimal(str(cfg.margin_buffer_pct / 100)))

        if margin_with_buffer > available_margin:
            return CheckResult(
                approved=False,
                reason=(
                    f"Insufficient margin: required {margin_with_buffer} "
                    f"(incl. {cfg.margin_buffer_pct}% buffer), "
                    f"available {available_margin}"
                ),
                check_name="margin",
                details={
                    "margin_required": str(margin_with_buffer),
                    "margin_available": str(available_margin),
                    "order_notional": str(order_notional),
                },
            )

        return CheckResult(approved=True, reason="", check_name="margin")

    def _check_wash_trade(self, order: OrderRequest) -> CheckResult:
        """Detect potential wash trades (rapid buy/sell in the same symbol).

        A wash trade is flagged when an order in the opposite direction
        for the same symbol was placed within the configured time window.
        """
        cfg = self._cfg(order.tenant_id)
        key = (order.tenant_id, order.symbol)
        window = timedelta(seconds=cfg.wash_trade_window_seconds)
        now = datetime.now(UTC)

        recent = self._recent_orders.get(key, [])
        # Prune stale entries
        recent = [(ts, side, qty) for ts, side, qty in recent if now - ts < window]
        self._recent_orders[key] = recent

        opposite_side = OrderSide.SELL if order.side == OrderSide.BUY else OrderSide.BUY
        for ts, side, qty in recent:
            if side == opposite_side.value:
                return CheckResult(
                    approved=False,
                    reason=(
                        f"Potential wash trade detected: {opposite_side} order for "
                        f"{order.symbol} was placed {int((now - ts).total_seconds())}s ago"
                    ),
                    check_name="wash_trade",
                    details={
                        "symbol": order.symbol,
                        "opposite_side": opposite_side.value,
                        "seconds_ago": int((now - ts).total_seconds()),
                    },
                )

        return CheckResult(approved=True, reason="", check_name="wash_trade")

    def _record_order(self, order: OrderRequest) -> None:
        """Record an order for future wash-trade detection."""
        key = (order.tenant_id, order.symbol)
        if key not in self._recent_orders:
            self._recent_orders[key] = []
        self._recent_orders[key].append(
            (datetime.now(UTC), order.side.value, order.qty)
        )


__all__ = [
    "CheckResult",
    "PreTradeCheckService",
    "PreTradeConfig",
]
