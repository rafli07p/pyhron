"""Pyhron pre-trade risk engine service.

Provides real-time pre-trade risk evaluation for all order flow. Consumes
strategy signals from Kafka, runs configurable risk checks, and publishes
risk decisions.

Modules:
    risk_engine_kafka_consumer: Main engine loop consuming signals and publishing decisions.
    pre_trade_risk_checks: Pure-function risk checks (lot size, position limits, VaR, etc.).
    portfolio_var_calculator: Parametric VaR estimation for portfolio risk measurement.
    circuit_breaker_state_manager: Redis-backed circuit breaker for halting/resuming trading.
    risk_limit_configuration: Per-strategy risk limit definitions.
"""

from services.pre_trade_risk_engine.circuit_breaker_state_manager import (
    CircuitBreakerStateManager,
)
from services.pre_trade_risk_engine.portfolio_var_calculator import (
    PortfolioVaRCalculator,
)
from services.pre_trade_risk_engine.pre_trade_risk_checks import (
    RiskCheckResult,
    check_buying_power_t2,
    check_daily_loss_limit,
    check_duplicate_order,
    check_lot_size_constraint,
    check_max_position_size,
    check_portfolio_var,
    check_sector_concentration,
    check_signal_staleness,
)
from services.pre_trade_risk_engine.risk_engine_kafka_consumer import (
    RiskEngineKafkaConsumer,
)
from services.pre_trade_risk_engine.risk_limit_configuration import (
    RiskLimitConfiguration,
)

__all__: list[str] = [
    "CircuitBreakerStateManager",
    "PortfolioVaRCalculator",
    "RiskCheckResult",
    "RiskEngineKafkaConsumer",
    "RiskLimitConfiguration",
    "check_buying_power_t2",
    "check_daily_loss_limit",
    "check_duplicate_order",
    "check_lot_size_constraint",
    "check_max_position_size",
    "check_portfolio_var",
    "check_sector_concentration",
    "check_signal_staleness",
]
