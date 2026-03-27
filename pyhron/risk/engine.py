from __future__ import annotations

from decimal import Decimal

from pyhron.risk.models import RiskCheckResult, RiskViolation, RiskViolationType
from pyhron.shared.schemas.order import OrderCreate, OrderSide
from pyhron.shared.schemas.risk import RiskLimits


class RiskEngine:
    def __init__(self, limits: RiskLimits) -> None:
        self.limits = limits
        self._last_prices: dict[str, Decimal] = {}

    def update_last_price(self, symbol: str, price: Decimal) -> None:
        self._last_prices[symbol] = price

    def _get_order_price(self, order: OrderCreate) -> Decimal:
        return order.price if order.price is not None else self._last_prices.get(order.symbol, Decimal("0"))

    def check_order_size(self, order: OrderCreate) -> RiskCheckResult:
        price = self._get_order_price(order)
        notional = order.quantity * price
        if notional > self.limits.max_order_size:
            return RiskCheckResult(
                passed=False,
                violations=[
                    RiskViolation(
                        violation_type=RiskViolationType.ORDER_SIZE_EXCEEDED,
                        message=f"Order notional {notional} exceeds limit {self.limits.max_order_size}",
                        current_value=notional,
                        limit_value=self.limits.max_order_size,
                    )
                ],
            )
        return RiskCheckResult(passed=True)

    def check_position_limit(self, order: OrderCreate, current_position_value: Decimal) -> RiskCheckResult:
        if order.side == OrderSide.SELL:
            return RiskCheckResult(passed=True)

        price = self._get_order_price(order)
        order_notional = order.quantity * price
        new_value = current_position_value + order_notional
        if new_value > self.limits.max_position_size:
            return RiskCheckResult(
                passed=False,
                violations=[
                    RiskViolation(
                        violation_type=RiskViolationType.POSITION_LIMIT_EXCEEDED,
                        message=f"Position value {new_value} would exceed limit {self.limits.max_position_size}",
                        current_value=new_value,
                        limit_value=self.limits.max_position_size,
                    )
                ],
            )
        return RiskCheckResult(passed=True)

    def check_var(self, current_var: Decimal, proposed_var_impact: Decimal) -> RiskCheckResult:
        new_var = current_var + proposed_var_impact
        warnings: list[str] | None = None

        if new_var > self.limits.max_var:
            return RiskCheckResult(
                passed=False,
                violations=[
                    RiskViolation(
                        violation_type=RiskViolationType.VAR_LIMIT_EXCEEDED,
                        message=f"VaR {new_var} would exceed limit {self.limits.max_var}",
                        current_value=new_var,
                        limit_value=self.limits.max_var,
                    )
                ],
            )

        warning_threshold = self.limits.max_var * Decimal("0.9")
        if new_var > warning_threshold:
            warnings = [f"VaR at {new_var} is above 90% of limit {self.limits.max_var}"]

        return RiskCheckResult(passed=True, warnings=warnings)

    def check_drawdown(self, peak_value: Decimal, current_value: Decimal) -> RiskCheckResult:
        if peak_value == Decimal("0"):
            return RiskCheckResult(passed=True)

        drawdown_pct = (peak_value - current_value) / peak_value
        if drawdown_pct > self.limits.max_drawdown_pct:
            return RiskCheckResult(
                passed=False,
                violations=[
                    RiskViolation(
                        violation_type=RiskViolationType.DRAWDOWN_EXCEEDED,
                        message=f"Drawdown {drawdown_pct:.4f} exceeds limit {self.limits.max_drawdown_pct}",
                        current_value=drawdown_pct,
                        limit_value=self.limits.max_drawdown_pct,
                    )
                ],
            )
        return RiskCheckResult(passed=True)

    def check_concentration(self, position_value: Decimal, total_portfolio_value: Decimal) -> RiskCheckResult:
        if total_portfolio_value == Decimal("0"):
            return RiskCheckResult(passed=True)

        concentration = position_value / total_portfolio_value
        if concentration > self.limits.max_concentration_pct:
            return RiskCheckResult(
                passed=False,
                violations=[
                    RiskViolation(
                        violation_type=RiskViolationType.CONCENTRATION_EXCEEDED,
                        message=f"Concentration {concentration:.4f} exceeds limit {self.limits.max_concentration_pct}",
                        current_value=concentration,
                        limit_value=self.limits.max_concentration_pct,
                    )
                ],
            )
        return RiskCheckResult(passed=True)

    def check_leverage(self, total_exposure: Decimal, equity: Decimal) -> RiskCheckResult:
        if equity == Decimal("0"):
            return RiskCheckResult(
                passed=False,
                violations=[
                    RiskViolation(
                        violation_type=RiskViolationType.LEVERAGE_EXCEEDED,
                        message="Cannot compute leverage with zero equity",
                        current_value=total_exposure,
                        limit_value=self.limits.max_leverage,
                    )
                ],
            )

        leverage = total_exposure / equity
        if leverage > self.limits.max_leverage:
            return RiskCheckResult(
                passed=False,
                violations=[
                    RiskViolation(
                        violation_type=RiskViolationType.LEVERAGE_EXCEEDED,
                        message=f"Leverage {leverage:.4f} exceeds limit {self.limits.max_leverage}",
                        current_value=leverage,
                        limit_value=self.limits.max_leverage,
                    )
                ],
            )
        return RiskCheckResult(passed=True)

    def run_pre_trade_checks(
        self,
        order: OrderCreate,
        current_position_value: Decimal,
        current_var: Decimal,
        proposed_var_impact: Decimal,
        peak_portfolio_value: Decimal,
        current_portfolio_value: Decimal,
        position_value_for_concentration: Decimal,
        total_portfolio_value: Decimal,
        total_exposure: Decimal,
        equity: Decimal,
    ) -> RiskCheckResult:
        checks = [
            self.check_order_size(order),
            self.check_position_limit(order, current_position_value),
            self.check_var(current_var, proposed_var_impact),
            self.check_drawdown(peak_portfolio_value, current_portfolio_value),
            self.check_concentration(position_value_for_concentration, total_portfolio_value),
            self.check_leverage(total_exposure, equity),
        ]

        all_violations: list[RiskViolation] = []
        all_warnings: list[str] = []
        passed = True

        for check in checks:
            if not check.passed:
                passed = False
            all_violations.extend(check.violations)
            if check.warnings:
                all_warnings.extend(check.warnings)

        return RiskCheckResult(
            passed=passed,
            violations=all_violations,
            warnings=all_warnings if all_warnings else None,
        )
