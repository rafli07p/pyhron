"""Risk limit engine with circuit-breaker protection.

Enforces configurable per-tenant position, order-size, daily-loss, and
portfolio VaR limits.  A ``pybreaker`` circuit breaker trips during
market crash scenarios to halt all order flow until manual reset.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal
from typing import Any

import numpy as np
import pybreaker
import structlog

logger = structlog.get_logger(__name__)


# ---------------------------------------------------------------------------
# Limit configuration
# ---------------------------------------------------------------------------

@dataclass
class TenantRiskLimits:
    """Per-tenant risk limit configuration.

    All monetary values are in the tenant's base currency.
    """

    # Position limits
    max_position_qty: Decimal = Decimal("100000")
    max_position_value: Decimal = Decimal("10000000")
    max_position_pct_nav: float = 10.0  # percent of NAV

    # Order size limits
    max_order_qty: Decimal = Decimal("50000")
    max_order_value: Decimal = Decimal("5000000")
    max_order_pct_adv: float = 5.0  # percent of average daily volume

    # Daily loss limits
    max_daily_loss: Decimal = Decimal("500000")
    max_daily_loss_pct_nav: float = 2.0

    # Portfolio VaR
    max_portfolio_var_95: Decimal = Decimal("1000000")
    max_portfolio_var_99: Decimal = Decimal("1500000")

    # Circuit breaker settings
    cb_fail_max: int = 5  # failures before circuit opens
    cb_reset_timeout: int = 300  # seconds before trying half-open


_DEFAULT_LIMITS = TenantRiskLimits()


# ---------------------------------------------------------------------------
# Check result
# ---------------------------------------------------------------------------

@dataclass
class LimitCheckResult:
    """Outcome of a single risk-limit check."""

    passed: bool
    limit_type: str
    current_value: Decimal
    limit_value: Decimal
    message: str = ""


# ---------------------------------------------------------------------------
# Risk limit engine
# ---------------------------------------------------------------------------

class RiskLimitEngine:
    """Enforces risk limits with pybreaker circuit-breaker protection.

    The circuit breaker monitors consecutive limit breaches.  When the
    failure threshold is reached (e.g. during a market crash) the
    breaker opens and *all* subsequent checks are automatically
    rejected until the cool-down period expires.

    Parameters
    ----------
    tenant_limits:
        Mapping of ``tenant_id`` -> ``TenantRiskLimits``.
    """

    def __init__(
        self,
        tenant_limits: dict[str, TenantRiskLimits] | None = None,
    ) -> None:
        self._tenant_limits = tenant_limits or {}
        self._log = logger.bind(component="RiskLimitEngine")

        # Per-tenant circuit breakers
        self._breakers: dict[str, pybreaker.CircuitBreaker] = {}

        # In-memory daily loss accumulator: {(tenant, date): Decimal}
        self._daily_losses: dict[tuple[str, date], Decimal] = {}

    def _get_limits(self, tenant_id: str) -> TenantRiskLimits:
        return self._tenant_limits.get(tenant_id, _DEFAULT_LIMITS)

    def _get_breaker(self, tenant_id: str) -> pybreaker.CircuitBreaker:
        if tenant_id not in self._breakers:
            limits = self._get_limits(tenant_id)
            self._breakers[tenant_id] = pybreaker.CircuitBreaker(
                fail_max=limits.cb_fail_max,
                reset_timeout=limits.cb_reset_timeout,
                name=f"risk_limit_{tenant_id}",
            )
        return self._breakers[tenant_id]

    # -- Limit checks -------------------------------------------------------

    def check_position_limit(
        self,
        tenant_id: str,
        symbol: str,
        current_qty: Decimal,
        current_value: Decimal,
        nav: Decimal | None = None,
    ) -> LimitCheckResult:
        """Check whether a position exceeds size or value limits.

        Parameters
        ----------
        current_qty:
            Absolute position quantity after the proposed trade.
        current_value:
            Absolute market value of the position.
        nav:
            Portfolio net-asset-value for percentage limit checks.
        """
        limits = self._get_limits(tenant_id)
        breaker = self._get_breaker(tenant_id)

        def _inner() -> LimitCheckResult:
            # Quantity check
            if abs(current_qty) > limits.max_position_qty:
                return LimitCheckResult(
                    passed=False,
                    limit_type="position_qty",
                    current_value=abs(current_qty),
                    limit_value=limits.max_position_qty,
                    message=f"Position qty {current_qty} exceeds limit {limits.max_position_qty} for {symbol}",
                )

            # Value check
            if abs(current_value) > limits.max_position_value:
                return LimitCheckResult(
                    passed=False,
                    limit_type="position_value",
                    current_value=abs(current_value),
                    limit_value=limits.max_position_value,
                    message=f"Position value {current_value} exceeds limit {limits.max_position_value} for {symbol}",
                )

            # NAV percentage check
            if nav is not None and nav > 0:
                pct = float(abs(current_value) / nav * 100)
                if pct > limits.max_position_pct_nav:
                    return LimitCheckResult(
                        passed=False,
                        limit_type="position_pct_nav",
                        current_value=Decimal(str(round(pct, 2))),
                        limit_value=Decimal(str(limits.max_position_pct_nav)),
                        message=f"Position {pct:.1f}% of NAV exceeds {limits.max_position_pct_nav}% for {symbol}",
                    )

            return LimitCheckResult(
                passed=True,
                limit_type="position",
                current_value=abs(current_value),
                limit_value=limits.max_position_value,
            )

        try:
            result = breaker.call(_inner)
        except pybreaker.CircuitBreakerError:
            self._log.error("circuit_breaker_open", tenant_id=tenant_id, check="position_limit")
            return LimitCheckResult(
                passed=False,
                limit_type="circuit_breaker",
                current_value=Decimal("0"),
                limit_value=Decimal("0"),
                message="Circuit breaker OPEN — all risk checks rejected",
            )

        if not result.passed:
            self._log.warning("position_limit_breach", tenant_id=tenant_id, symbol=symbol, msg=result.message)
            breaker.call(lambda: (_ for _ in ()).throw(RuntimeError("limit breach")))  # noqa: B023
        return result

    def check_order_size_limit(
        self,
        tenant_id: str,
        symbol: str,
        order_qty: Decimal,
        order_value: Decimal,
        avg_daily_volume: Decimal | None = None,
    ) -> LimitCheckResult:
        """Check whether a single order exceeds size limits."""
        limits = self._get_limits(tenant_id)
        breaker = self._get_breaker(tenant_id)

        def _inner() -> LimitCheckResult:
            if abs(order_qty) > limits.max_order_qty:
                return LimitCheckResult(
                    passed=False,
                    limit_type="order_qty",
                    current_value=abs(order_qty),
                    limit_value=limits.max_order_qty,
                    message=f"Order qty {order_qty} exceeds limit {limits.max_order_qty} for {symbol}",
                )

            if abs(order_value) > limits.max_order_value:
                return LimitCheckResult(
                    passed=False,
                    limit_type="order_value",
                    current_value=abs(order_value),
                    limit_value=limits.max_order_value,
                    message=f"Order value {order_value} exceeds limit {limits.max_order_value} for {symbol}",
                )

            if avg_daily_volume is not None and avg_daily_volume > 0:
                pct = float(abs(order_qty) / avg_daily_volume * 100)
                if pct > limits.max_order_pct_adv:
                    return LimitCheckResult(
                        passed=False,
                        limit_type="order_pct_adv",
                        current_value=Decimal(str(round(pct, 2))),
                        limit_value=Decimal(str(limits.max_order_pct_adv)),
                        message=f"Order is {pct:.1f}% of ADV, exceeds {limits.max_order_pct_adv}%",
                    )

            return LimitCheckResult(
                passed=True,
                limit_type="order_size",
                current_value=abs(order_value),
                limit_value=limits.max_order_value,
            )

        try:
            result = breaker.call(_inner)
        except pybreaker.CircuitBreakerError:
            self._log.error("circuit_breaker_open", tenant_id=tenant_id, check="order_size")
            return LimitCheckResult(
                passed=False,
                limit_type="circuit_breaker",
                current_value=Decimal("0"),
                limit_value=Decimal("0"),
                message="Circuit breaker OPEN — all risk checks rejected",
            )

        if not result.passed:
            self._log.warning("order_size_breach", tenant_id=tenant_id, symbol=symbol, msg=result.message)
        return result

    def check_daily_loss_limit(
        self,
        tenant_id: str,
        current_daily_pnl: Decimal,
        nav: Decimal | None = None,
    ) -> LimitCheckResult:
        """Check whether the daily loss limit has been breached.

        Parameters
        ----------
        current_daily_pnl:
            Today's cumulative P&L (negative = loss).
        """
        limits = self._get_limits(tenant_id)
        breaker = self._get_breaker(tenant_id)
        today = date.today()

        # Track running daily loss
        self._daily_losses[(tenant_id, today)] = current_daily_pnl

        def _inner() -> LimitCheckResult:
            loss = abs(min(current_daily_pnl, Decimal("0")))

            if loss > limits.max_daily_loss:
                return LimitCheckResult(
                    passed=False,
                    limit_type="daily_loss",
                    current_value=loss,
                    limit_value=limits.max_daily_loss,
                    message=f"Daily loss {loss} exceeds limit {limits.max_daily_loss}",
                )

            if nav is not None and nav > 0:
                pct = float(loss / nav * 100)
                if pct > limits.max_daily_loss_pct_nav:
                    return LimitCheckResult(
                        passed=False,
                        limit_type="daily_loss_pct_nav",
                        current_value=Decimal(str(round(pct, 2))),
                        limit_value=Decimal(str(limits.max_daily_loss_pct_nav)),
                        message=f"Daily loss is {pct:.1f}% of NAV, exceeds {limits.max_daily_loss_pct_nav}%",
                    )

            return LimitCheckResult(
                passed=True,
                limit_type="daily_loss",
                current_value=loss,
                limit_value=limits.max_daily_loss,
            )

        try:
            result = breaker.call(_inner)
        except pybreaker.CircuitBreakerError:
            self._log.error("circuit_breaker_open", tenant_id=tenant_id, check="daily_loss")
            return LimitCheckResult(
                passed=False,
                limit_type="circuit_breaker",
                current_value=Decimal("0"),
                limit_value=Decimal("0"),
                message="Circuit breaker OPEN — all risk checks rejected",
            )

        if not result.passed:
            self._log.error("daily_loss_breach", tenant_id=tenant_id, pnl=str(current_daily_pnl))
            # Trip the breaker on daily loss breach
            try:
                breaker.call(lambda: (_ for _ in ()).throw(RuntimeError("daily loss breach")))
            except (RuntimeError, pybreaker.CircuitBreakerError):
                pass
        return result

    def check_portfolio_var(
        self,
        tenant_id: str,
        returns: np.ndarray,
        portfolio_value: Decimal,
        confidence_level: float = 0.95,
    ) -> LimitCheckResult:
        """Check portfolio Value-at-Risk against configured limits.

        Uses historical simulation: the VaR is the *confidence_level*
        percentile of the empirical return distribution applied to the
        current portfolio value.

        Parameters
        ----------
        returns:
            Array of historical daily portfolio returns.
        portfolio_value:
            Current total portfolio market value.
        confidence_level:
            VaR confidence (0.95 or 0.99).
        """
        limits = self._get_limits(tenant_id)
        breaker = self._get_breaker(tenant_id)

        def _inner() -> LimitCheckResult:
            if len(returns) < 2:
                return LimitCheckResult(
                    passed=True,
                    limit_type="portfolio_var",
                    current_value=Decimal("0"),
                    limit_value=limits.max_portfolio_var_95,
                    message="Insufficient return history for VaR calculation",
                )

            var_pctile = np.percentile(returns, (1 - confidence_level) * 100)
            var_value = abs(float(var_pctile) * float(portfolio_value))
            var_decimal = Decimal(str(round(var_value, 2)))

            limit = limits.max_portfolio_var_95 if confidence_level <= 0.95 else limits.max_portfolio_var_99

            if var_decimal > limit:
                return LimitCheckResult(
                    passed=False,
                    limit_type=f"portfolio_var_{int(confidence_level * 100)}",
                    current_value=var_decimal,
                    limit_value=limit,
                    message=f"Portfolio VaR({confidence_level:.0%}) = {var_decimal} exceeds limit {limit}",
                )

            return LimitCheckResult(
                passed=True,
                limit_type=f"portfolio_var_{int(confidence_level * 100)}",
                current_value=var_decimal,
                limit_value=limit,
            )

        try:
            result = breaker.call(_inner)
        except pybreaker.CircuitBreakerError:
            self._log.error("circuit_breaker_open", tenant_id=tenant_id, check="portfolio_var")
            return LimitCheckResult(
                passed=False,
                limit_type="circuit_breaker",
                current_value=Decimal("0"),
                limit_value=Decimal("0"),
                message="Circuit breaker OPEN — all risk checks rejected",
            )

        if not result.passed:
            self._log.warning("var_breach", tenant_id=tenant_id, msg=result.message)
        return result

    # -- Circuit breaker management ------------------------------------------

    def get_breaker_state(self, tenant_id: str) -> str:
        """Return the current circuit breaker state for a tenant."""
        breaker = self._get_breaker(tenant_id)
        return breaker.current_state

    def reset_breaker(self, tenant_id: str) -> None:
        """Manually reset the circuit breaker for a tenant."""
        if tenant_id in self._breakers:
            self._breakers[tenant_id] = pybreaker.CircuitBreaker(
                fail_max=self._get_limits(tenant_id).cb_fail_max,
                reset_timeout=self._get_limits(tenant_id).cb_reset_timeout,
                name=f"risk_limit_{tenant_id}",
            )
            self._log.info("circuit_breaker_reset", tenant_id=tenant_id)


__all__ = [
    "TenantRiskLimits",
    "LimitCheckResult",
    "RiskLimitEngine",
]
