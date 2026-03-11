"""Backtest run model.

Records the full lifecycle and performance metrics of a strategy backtest,
including a frozen snapshot of parameters used at run time.
"""

import enum
import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import Date, ForeignKey, Integer, Numeric, Text
from sqlalchemy.dialects.postgresql import ENUM, JSONB, TIMESTAMP, UUID
from sqlalchemy.orm import Mapped, mapped_column

from shared.async_database_session import Base


class BacktestStatus(enum.StrEnum):
    """Backtest run lifecycle status."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class BacktestRun(Base):
    """Backtest execution record with performance metrics.

    Attributes:
        id: UUID primary key.
        strategy_id: FK to the strategy being tested.
        user_id: FK to the user who initiated the backtest.
        status: Current lifecycle status.
        start_date: Backtest window start.
        end_date: Backtest window end.
        initial_capital_idr: Starting capital in IDR.
        final_capital_idr: Ending capital in IDR.
        total_return_pct: Total return percentage.
        cagr_pct: Compound annual growth rate.
        sharpe_ratio: Risk-adjusted return (Sharpe).
        sortino_ratio: Downside risk-adjusted return (Sortino).
        calmar_ratio: Return / max drawdown.
        max_drawdown_pct: Maximum peak-to-trough decline.
        max_drawdown_duration_days: Longest drawdown period in days.
        total_trades: Total number of trades executed.
        win_rate_pct: Percentage of winning trades.
        profit_factor: Gross profit / gross loss.
        omega_ratio: Probability-weighted ratio of gains vs losses.
        parameters_snapshot: Frozen copy of strategy parameters at run time.
        error_message: Error details if status is FAILED.
        started_at: Actual execution start timestamp.
        completed_at: Actual execution completion timestamp.
        created_at: Row creation timestamp.
    """

    __tablename__ = "backtest_runs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    strategy_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("strategies.id", ondelete="CASCADE"),
        nullable=False,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    status: Mapped[BacktestStatus] = mapped_column(
        ENUM(BacktestStatus, name="backtest_status", create_type=False),
        nullable=False,
        default=BacktestStatus.PENDING,
    )
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    end_date: Mapped[date] = mapped_column(Date, nullable=False)
    initial_capital_idr: Mapped[Decimal] = mapped_column(Numeric(30, 2), nullable=False)
    final_capital_idr: Mapped[Decimal | None] = mapped_column(Numeric(30, 2))
    total_return_pct: Mapped[Decimal | None] = mapped_column(Numeric(10, 4))
    cagr_pct: Mapped[Decimal | None] = mapped_column(Numeric(10, 4))
    sharpe_ratio: Mapped[Decimal | None] = mapped_column(Numeric(10, 4))
    sortino_ratio: Mapped[Decimal | None] = mapped_column(Numeric(10, 4))
    calmar_ratio: Mapped[Decimal | None] = mapped_column(Numeric(10, 4))
    max_drawdown_pct: Mapped[Decimal | None] = mapped_column(Numeric(10, 4))
    max_drawdown_duration_days: Mapped[int | None] = mapped_column(Integer)
    total_trades: Mapped[int | None] = mapped_column(Integer)
    win_rate_pct: Mapped[Decimal | None] = mapped_column(Numeric(10, 4))
    profit_factor: Mapped[Decimal | None] = mapped_column(Numeric(10, 4))
    omega_ratio: Mapped[Decimal | None] = mapped_column(Numeric(10, 4))
    parameters_snapshot: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    error_message: Mapped[str | None] = mapped_column(Text)
    started_at: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True))
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), server_default="now()")
