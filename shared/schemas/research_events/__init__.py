"""Research event schemas for the Pyhron trading platform.

Defines Pydantic v2 models for backtesting workflows, strategy
evaluation results, and quantitative factor analysis.  All models
enforce multi-tenancy via mandatory ``tenant_id`` fields.
"""

from __future__ import annotations

from datetime import UTC, date, datetime
from decimal import Decimal
from enum import StrEnum
from typing import Optional
from uuid import UUID, uuid4

from pydantic import BaseModel, Field, model_validator

# ---------------------------------------------------------------------------
# Enumerations
# ---------------------------------------------------------------------------

class BacktestStatus(StrEnum):
    """Lifecycle status of a backtest job."""

    QUEUED = "QUEUED"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


class FactorCategory(StrEnum):
    """Quantitative factor categories."""

    VALUE = "VALUE"
    MOMENTUM = "MOMENTUM"
    QUALITY = "QUALITY"
    SIZE = "SIZE"
    VOLATILITY = "VOLATILITY"
    GROWTH = "GROWTH"
    LIQUIDITY = "LIQUIDITY"
    SENTIMENT = "SENTIMENT"
    CUSTOM = "CUSTOM"


class Frequency(StrEnum):
    """Return / rebalance frequency."""

    DAILY = "DAILY"
    WEEKLY = "WEEKLY"
    MONTHLY = "MONTHLY"
    QUARTERLY = "QUARTERLY"
    ANNUAL = "ANNUAL"


class SimulationType(StrEnum):
    """Monte Carlo simulation method."""

    GBM = "GBM"
    JUMP_DIFFUSION = "JUMP_DIFFUSION"
    HESTON = "HESTON"
    HISTORICAL_BOOTSTRAP = "HISTORICAL_BOOTSTRAP"


# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------

class ResearchEventBase(BaseModel):
    """Base class for all research events."""

    model_config = {"str_strip_whitespace": True}

    event_id: UUID = Field(default_factory=uuid4, description="Unique event identifier")
    tenant_id: str = Field(..., min_length=1, max_length=64, description="Tenant identifier for multi-tenancy")
    timestamp: datetime = Field(default_factory=lambda: datetime.now(tz=UTC), description="Event timestamp (UTC)")


class BacktestRequest(ResearchEventBase):
    """Request to run a strategy backtest.

    Submitted by a quant researcher via the API or the research
    notebook environment.  The backtesting engine picks this up,
    executes the strategy over historical data, and publishes a
    ``BacktestResult``.
    """

    strategy_id: str = Field(..., min_length=1, max_length=128, description="Strategy identifier / name")
    strategy_version: str | None = Field(default=None, max_length=64, description="Strategy version tag")
    start_date: date = Field(..., description="Backtest start date (inclusive)")
    end_date: date = Field(..., description="Backtest end date (inclusive)")
    symbols: list[str] = Field(..., min_length=1, description="Universe of symbols to include")
    benchmark: str | None = Field(default=None, max_length=20, description="Benchmark symbol (e.g. SPY)")
    initial_capital: Decimal = Field(default=Decimal("1000000"), gt=0, description="Starting capital")
    frequency: Frequency = Field(default=Frequency.DAILY, description="Return calculation frequency")
    slippage_bps: Decimal = Field(default=Decimal("5"), ge=0, description="Assumed slippage in basis points")
    commission_per_share: Decimal = Field(default=Decimal("0.005"), ge=0, description="Commission per share")
    parameters: dict[str, str | int | float | bool] = Field(
        default_factory=dict,
        description="Strategy-specific parameters",
    )

    @model_validator(mode="after")
    def _validate_dates(self) -> BacktestRequest:
        if self.start_date >= self.end_date:
            raise ValueError("start_date must be before end_date")
        return self


class BacktestResult(ResearchEventBase):
    """Results of a completed backtest run.

    Contains all key performance metrics needed to evaluate a strategy
    including risk-adjusted returns, drawdown analysis, and trade
    statistics.
    """

    strategy_id: str = Field(..., min_length=1, max_length=128, description="Strategy identifier")
    backtest_id: UUID = Field(default_factory=uuid4, description="Unique backtest run identifier")
    status: BacktestStatus = Field(default=BacktestStatus.COMPLETED, description="Backtest job status")
    start_date: date = Field(..., description="Actual backtest start date")
    end_date: date = Field(..., description="Actual backtest end date")
    symbols: list[str] = Field(default_factory=list, description="Symbols included in the backtest")

    # -- Performance metrics --
    total_return: Decimal = Field(default=Decimal("0"), description="Total return (e.g. 0.25 = 25%)")
    annualized_return: Decimal = Field(default=Decimal("0"), description="Annualized return")
    sharpe_ratio: Decimal | None = Field(default=None, description="Annualized Sharpe ratio")
    sortino_ratio: Decimal | None = Field(default=None, description="Sortino ratio")
    calmar_ratio: Decimal | None = Field(default=None, description="Calmar ratio")
    max_drawdown: Decimal = Field(default=Decimal("0"), le=0, description="Maximum drawdown (negative)")
    max_drawdown_duration_days: int | None = Field(default=None, ge=0, description="Longest drawdown in days")
    volatility: Decimal | None = Field(default=None, ge=0, description="Annualized volatility")
    beta: Decimal | None = Field(default=None, description="Portfolio beta to benchmark")
    alpha: Decimal | None = Field(default=None, description="Jensen's alpha")
    information_ratio: Decimal | None = Field(default=None, description="Information ratio")

    # -- Trade statistics --
    total_trades: int = Field(default=0, ge=0, description="Total number of trades")
    win_rate: Decimal | None = Field(default=None, ge=0, le=1, description="Fraction of winning trades")
    profit_factor: Decimal | None = Field(default=None, ge=0, description="Gross profit / gross loss")
    avg_trade_pnl: Decimal | None = Field(default=None, description="Average P&L per trade")
    avg_holding_period_days: Decimal | None = Field(default=None, ge=0, description="Avg holding period")

    # -- Costs --
    total_commission: Decimal = Field(default=Decimal("0"), ge=0, description="Total commissions paid")
    total_slippage: Decimal = Field(default=Decimal("0"), ge=0, description="Total estimated slippage cost")

    # -- Time series (stored as JSON-serializable lists) --
    returns: list[float] = Field(default_factory=list, description="Period return series")
    equity_curve: list[float] = Field(default_factory=list, description="Equity curve values")

    initial_capital: Decimal = Field(default=Decimal("1000000"), gt=0, description="Starting capital")
    final_capital: Decimal = Field(default=Decimal("0"), ge=0, description="Ending capital")
    currency: str = Field(default="USD", max_length=3, description="Reporting currency")
    error_message: str | None = Field(default=None, max_length=2048, description="Error details if failed")


class FactorResult(ResearchEventBase):
    """Quantitative factor analysis result.

    Output of a factor model evaluation, containing exposures, returns,
    and statistical significance for a given factor over a specified
    universe and time window.
    """

    strategy_id: str | None = Field(default=None, max_length=128, description="Associated strategy")
    factor_name: str = Field(..., min_length=1, max_length=128, description="Factor name (e.g. 'Earnings Yield')")
    factor_category: FactorCategory = Field(default=FactorCategory.CUSTOM, description="Factor category")
    start_date: date = Field(..., description="Analysis start date")
    end_date: date = Field(..., description="Analysis end date")
    symbols: list[str] = Field(default_factory=list, description="Universe of symbols analyzed")
    frequency: Frequency = Field(default=Frequency.MONTHLY, description="Rebalance frequency")

    # -- Factor metrics --
    returns: list[float] = Field(default_factory=list, description="Factor return series")
    cumulative_return: Decimal = Field(default=Decimal("0"), description="Cumulative factor return")
    annualized_return: Decimal = Field(default=Decimal("0"), description="Annualized factor return")
    sharpe_ratio: Decimal | None = Field(default=None, description="Factor Sharpe ratio")
    max_drawdown: Decimal = Field(default=Decimal("0"), le=0, description="Maximum drawdown (negative)")
    t_statistic: Decimal | None = Field(default=None, description="T-statistic of factor return")
    p_value: Decimal | None = Field(default=None, ge=0, le=1, description="P-value of factor return")
    ic_mean: Decimal | None = Field(default=None, description="Mean information coefficient")
    ic_ir: Decimal | None = Field(default=None, description="IC information ratio (IC mean / IC std)")
    turnover: Decimal | None = Field(default=None, ge=0, description="Average portfolio turnover")

    # -- Quintile / decile spreads --
    long_short_return: Decimal | None = Field(default=None, description="Long-short portfolio return")
    quintile_returns: list[float] = Field(
        default_factory=list,
        description="Average returns per quintile (Q1..Q5)",
    )

    @model_validator(mode="after")
    def _validate_dates(self) -> FactorResult:
        if self.start_date >= self.end_date:
            raise ValueError("start_date must be before end_date")
        return self


__all__ = [
    "BacktestRequest",
    "BacktestResult",
    "BacktestStatus",
    "FactorCategory",
    "FactorResult",
    "Frequency",
    "ResearchEventBase",
    "SimulationType",
]
