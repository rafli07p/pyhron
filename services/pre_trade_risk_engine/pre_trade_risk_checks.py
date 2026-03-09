"""Pre-trade risk checks executed synchronously before every order.

Design constraint (for Rust migration):
  Every check is a pure function: (OrderRequest, PortfolioState, RiskLimits) -> RiskCheckResult
  No side effects inside checks. Side effects (logging, DB writes) happen in the engine.
  This design means Rust can replace individual check functions independently.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

from google.protobuf.timestamp_pb2 import Timestamp

from shared.proto_generated.equity_orders_pb2 import OrderRequest
from shared.proto_generated.equity_positions_pb2 import PortfolioSnapshot


@dataclass(frozen=True)
class RiskCheckResult:
    """Outcome of a single risk check.

    Attributes:
        passed: Whether the check passed (True) or failed (False).
        check_name: Identifier for the check that produced this result.
        reason: Human-readable explanation if the check failed.
        adjusted_quantity: Suggested adjusted quantity if the check failed
            due to a quantity constraint.
    """

    passed: bool
    check_name: str
    reason: str | None = None
    adjusted_quantity: int | None = None


def check_lot_size_constraint(
    order: OrderRequest,
    lot_size: int = 100,
) -> RiskCheckResult:
    """Validate that order quantity is a positive multiple of the IDX lot size.

    IDX-specific: all equity orders must be in multiples of 100 shares (1 lot).

    Args:
        order: The order request to validate.
        lot_size: The lot size to enforce (default 100 for IDX).

    Returns:
        RiskCheckResult indicating pass/fail with adjusted quantity if applicable.
    """
    if order.quantity <= 0:
        return RiskCheckResult(
            passed=False,
            check_name="lot_size",
            reason=f"Quantity must be positive, got {order.quantity}",
        )
    if order.quantity % lot_size != 0:
        nearest = (order.quantity // lot_size) * lot_size
        return RiskCheckResult(
            passed=False,
            check_name="lot_size",
            reason=(
                f"Quantity {order.quantity} is not a multiple of lot_size "
                f"{lot_size}. Nearest valid: {nearest}"
            ),
            adjusted_quantity=nearest if nearest > 0 else None,
        )
    return RiskCheckResult(passed=True, check_name="lot_size")


def check_max_position_size(
    order: OrderRequest,
    portfolio: PortfolioSnapshot,
    max_pct: float,
) -> RiskCheckResult:
    """Validate that post-trade position does not exceed max percentage of portfolio.

    After this fill, no single symbol should exceed ``max_pct`` of total
    portfolio value.

    Args:
        order: The order request to validate.
        portfolio: Current portfolio snapshot.
        max_pct: Maximum allowed position size as a fraction of portfolio value.

    Returns:
        RiskCheckResult with adjusted quantity if the limit would be breached.
    """
    total_value = portfolio.total_market_value + portfolio.cash_balance
    if total_value <= 0:
        return RiskCheckResult(
            passed=False,
            check_name="max_position_size",
            reason="Portfolio total value is zero or negative",
        )

    # Find existing position for this symbol
    existing_qty = 0
    current_price = 0.0
    for pos in portfolio.positions:
        if pos.symbol == order.symbol:
            existing_qty = pos.quantity
            current_price = pos.current_price
            break

    # Use limit_price for valuation if available, else current_price
    price = order.limit_price if order.limit_price > 0 else current_price
    if price <= 0:
        return RiskCheckResult(
            passed=True,
            check_name="max_position_size",
            reason="Cannot value order -- no price available, passing with warning",
        )

    # Compute post-trade position value
    if order.side == 1:  # BUY
        new_qty = existing_qty + order.quantity
    else:  # SELL
        new_qty = existing_qty - order.quantity

    position_value = abs(new_qty) * price
    position_pct = position_value / total_value

    if position_pct > max_pct:
        # Compute adjusted quantity that stays within limit
        max_value = max_pct * total_value
        max_qty = int(max_value / price)
        if order.side == 1:  # BUY
            allowed_additional = max_qty - existing_qty
        else:
            allowed_additional = order.quantity  # sells reduce exposure

        return RiskCheckResult(
            passed=False,
            check_name="max_position_size",
            reason=(
                f"Position would be {position_pct:.1%} of portfolio "
                f"(limit: {max_pct:.1%})"
            ),
            adjusted_quantity=max(0, allowed_additional),
        )

    return RiskCheckResult(passed=True, check_name="max_position_size")


def check_sector_concentration(
    order: OrderRequest,
    portfolio: PortfolioSnapshot,
    sector_map: dict[str, str],
    max_pct: float,
) -> RiskCheckResult:
    """Validate that post-trade sector exposure does not exceed the limit.

    After this fill, no single sector should exceed ``max_pct`` of total
    portfolio value.

    Args:
        order: The order request to validate.
        portfolio: Current portfolio snapshot.
        sector_map: Mapping of symbol to sector name.
        max_pct: Maximum allowed sector concentration as a fraction.

    Returns:
        RiskCheckResult indicating whether the sector limit would be breached.
    """
    total_value = portfolio.total_market_value + portfolio.cash_balance
    if total_value <= 0:
        return RiskCheckResult(passed=True, check_name="sector_concentration")

    target_sector = sector_map.get(order.symbol, "UNKNOWN")
    if target_sector == "UNKNOWN":
        return RiskCheckResult(passed=True, check_name="sector_concentration")

    # Sum existing sector exposure
    sector_value = 0.0
    for pos in portfolio.positions:
        if sector_map.get(pos.symbol) == target_sector:
            sector_value += pos.market_value

    # Add this order's value
    price = order.limit_price if order.limit_price > 0 else 0.0
    if price > 0 and order.side == 1:  # BUY increases exposure
        sector_value += order.quantity * price

    sector_pct = sector_value / total_value
    if sector_pct > max_pct:
        return RiskCheckResult(
            passed=False,
            check_name="sector_concentration",
            reason=(
                f"Sector '{target_sector}' would be {sector_pct:.1%} of portfolio "
                f"(limit: {max_pct:.1%})"
            ),
        )
    return RiskCheckResult(passed=True, check_name="sector_concentration")


def check_daily_loss_limit(
    portfolio: PortfolioSnapshot,
    daily_loss_limit_pct: float,
) -> RiskCheckResult:
    """Circuit breaker: reject all orders if daily loss exceeds threshold.

    Args:
        portfolio: Current portfolio snapshot with P&L data.
        daily_loss_limit_pct: Maximum allowed daily loss as a fraction.

    Returns:
        RiskCheckResult indicating whether the daily loss limit is breached.
    """
    total_value = portfolio.total_market_value + portfolio.cash_balance
    if total_value <= 0:
        return RiskCheckResult(
            passed=False,
            check_name="daily_loss_limit",
            reason="Portfolio value is zero or negative -- circuit breaker triggered",
        )

    daily_pnl = portfolio.total_unrealized_pnl + portfolio.total_realized_pnl_today
    daily_pnl_pct = daily_pnl / total_value

    if daily_pnl_pct < -daily_loss_limit_pct:
        return RiskCheckResult(
            passed=False,
            check_name="daily_loss_limit",
            reason=(
                f"Daily loss {daily_pnl_pct:.2%} exceeds limit "
                f"-{daily_loss_limit_pct:.2%}. Trading halted."
            ),
        )
    return RiskCheckResult(passed=True, check_name="daily_loss_limit")


def check_buying_power_t2(
    order: OrderRequest,
    available_cash: float,
    current_price: float,
) -> RiskCheckResult:
    """Validate buying power under IDX T+2 settlement rules.

    IDX T+2: proceeds from sells are not available for 2 business days.
    Only applies to BUY orders.

    Args:
        order: The order request to validate.
        available_cash: Cash available under T+2 settlement.
        current_price: Current market price of the instrument.

    Returns:
        RiskCheckResult indicating whether buying power is sufficient.
    """
    if order.side != 1:  # Only check for BUY orders
        return RiskCheckResult(passed=True, check_name="buying_power_t2")

    price = order.limit_price if order.limit_price > 0 else current_price
    if price <= 0:
        return RiskCheckResult(passed=True, check_name="buying_power_t2")

    required_cash = order.quantity * price
    if required_cash > available_cash:
        return RiskCheckResult(
            passed=False,
            check_name="buying_power_t2",
            reason=(
                f"Required cash {required_cash:,.0f} exceeds available "
                f"T+2 buying power {available_cash:,.0f}"
            ),
        )
    return RiskCheckResult(passed=True, check_name="buying_power_t2")


def check_duplicate_order(
    order: OrderRequest,
    recent_orders: list[str],
) -> RiskCheckResult:
    """Reject if client_order_id was already submitted (idempotency guard).

    Args:
        order: The order request to check.
        recent_orders: List of recently submitted client_order_ids.

    Returns:
        RiskCheckResult indicating whether the order is a duplicate.
    """
    if order.client_order_id in recent_orders:
        return RiskCheckResult(
            passed=False,
            check_name="duplicate_order",
            reason=f"Duplicate client_order_id: {order.client_order_id}",
        )
    return RiskCheckResult(passed=True, check_name="duplicate_order")


def check_signal_staleness(
    order: OrderRequest,
    max_age_seconds: int = 300,
) -> RiskCheckResult:
    """Reject order if signal_time is older than max_age_seconds.

    Ensures that only fresh signals are acted upon, preventing stale
    signals from generating orders in changed market conditions.

    Args:
        order: The order request containing the signal timestamp.
        max_age_seconds: Maximum allowed signal age in seconds.

    Returns:
        RiskCheckResult indicating whether the signal is fresh enough.
    """
    if not order.HasField("signal_time"):
        return RiskCheckResult(
            passed=False,
            check_name="signal_staleness",
            reason="Order has no signal_time -- cannot verify freshness",
        )

    signal_dt = order.signal_time.ToDatetime().replace(tzinfo=timezone.utc)
    now = datetime.now(tz=timezone.utc)
    age = (now - signal_dt).total_seconds()

    if age > max_age_seconds:
        return RiskCheckResult(
            passed=False,
            check_name="signal_staleness",
            reason=f"Signal age {age:.0f}s exceeds max {max_age_seconds}s",
        )
    return RiskCheckResult(passed=True, check_name="signal_staleness")


def check_portfolio_var(
    order: OrderRequest,
    portfolio: PortfolioSnapshot,
    var_limit_pct: float,
) -> RiskCheckResult:
    """Estimate incremental VaR contribution of this order.

    Uses simplified parametric VaR (Gaussian assumption) for speed.
    Reject if portfolio VaR would exceed ``var_limit_pct``.

    Args:
        order: The order request to evaluate.
        portfolio: Current portfolio snapshot with VaR data.
        var_limit_pct: Maximum allowed portfolio VaR as a fraction.

    Returns:
        RiskCheckResult indicating whether the VaR limit would be breached.
    """
    total_value = portfolio.total_market_value + portfolio.cash_balance
    if total_value <= 0:
        return RiskCheckResult(passed=True, check_name="portfolio_var")

    current_var_pct = portfolio.portfolio_var_95 / total_value if total_value > 0 else 0

    # Simplified incremental VaR: assume linear contribution
    # In production, use covariance matrix for proper computation
    price = order.limit_price if order.limit_price > 0 else 0.0
    if price <= 0:
        return RiskCheckResult(passed=True, check_name="portfolio_var")

    order_value = order.quantity * price
    # Conservative estimate: assume order adds proportional VaR
    estimated_var_pct = current_var_pct + (order_value / total_value) * 0.02  # 2% daily vol assumption

    if estimated_var_pct > var_limit_pct:
        return RiskCheckResult(
            passed=False,
            check_name="portfolio_var",
            reason=(
                f"Estimated portfolio VaR {estimated_var_pct:.2%} would exceed "
                f"limit {var_limit_pct:.2%}"
            ),
        )
    return RiskCheckResult(passed=True, check_name="portfolio_var")
