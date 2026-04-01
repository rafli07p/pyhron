"""Paper trading session, NAV snapshot, and P&L attribution models.

Tracks paper trading runs with equity curve snapshots and per-symbol
profit attribution for strategy performance analysis.
"""

import uuid
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import (
    CheckConstraint,
    Date,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    PrimaryKeyConstraint,
    String,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import TIMESTAMP, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from shared.async_database_session import Base


class PyhronPaperTradingSession(Base):
    """A single paper trading run for a strategy.

    Attributes:
        id: UUID primary key.
        name: Human-readable session name.
        strategy_id: FK to originating strategy.
        status: INITIALIZING, RUNNING, PAUSED, STOPPED, COMPLETED.
        mode: LIVE_HOURS or SIMULATION.
        initial_capital_idr: Starting capital in IDR.
        current_nav_idr: Current net asset value.
        peak_nav_idr: Highest NAV reached (for drawdown calculation).
        max_drawdown_pct: Maximum drawdown percentage.
        total_trades: Total number of fills.
        winning_trades: Number of fills with positive realized P&L.
        realized_pnl_idr: Cumulative realized P&L.
        total_commission_idr: Cumulative transaction costs.
        cash_idr: Settled cash balance.
        unsettled_cash_idr: Cash from T+0/T+1 sells, not yet settled.
        started_at: When session entered RUNNING state.
        paused_at: When session was last paused.
        stopped_at: When session was stopped.
        created_by: FK to user who created the session.
    """

    __tablename__ = "pyhron_paper_trading_session"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    strategy_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("pyhron_strategy.id", ondelete="CASCADE"),
        nullable=False,
    )
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="INITIALIZING")
    mode: Mapped[str] = mapped_column(String(20), nullable=False)
    initial_capital_idr: Mapped[Decimal] = mapped_column(Numeric(20, 2), nullable=False)
    current_nav_idr: Mapped[Decimal] = mapped_column(Numeric(20, 2), nullable=False)
    peak_nav_idr: Mapped[Decimal] = mapped_column(Numeric(20, 2), nullable=False)
    max_drawdown_pct: Mapped[Decimal] = mapped_column(Numeric(8, 4), nullable=False, default=Decimal("0"))
    total_trades: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    winning_trades: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    realized_pnl_idr: Mapped[Decimal] = mapped_column(Numeric(20, 2), nullable=False, default=Decimal("0"))
    total_commission_idr: Mapped[Decimal] = mapped_column(Numeric(20, 2), nullable=False, default=Decimal("0"))
    cash_idr: Mapped[Decimal] = mapped_column(Numeric(20, 2), nullable=False, default=Decimal("0"))
    unsettled_cash_idr: Mapped[Decimal] = mapped_column(Numeric(20, 2), nullable=False, default=Decimal("0"))
    started_at: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True))
    paused_at: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True))
    stopped_at: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True))
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), server_default="now()")
    updated_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), server_default="now()")
    created_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("pyhron_user.id"),
    )

    strategy = relationship("PyhronStrategy", back_populates="paper_sessions", lazy="selectin")
    creator = relationship("PyhronUser", lazy="selectin")
    nav_snapshots = relationship("PyhronPaperNavSnapshot", back_populates="session", lazy="selectin")
    pnl_attributions = relationship("PyhronPaperPnlAttribution", back_populates="session", lazy="selectin")

    __table_args__ = (
        CheckConstraint("initial_capital_idr > 0", name="ck_paper_session_capital_positive"),
        CheckConstraint(
            "status IN ('INITIALIZING', 'RUNNING', 'PAUSED', 'STOPPED', 'COMPLETED')",
            name="ck_paper_session_status_valid",
        ),
        CheckConstraint(
            "mode IN ('LIVE_HOURS', 'SIMULATION')",
            name="ck_paper_session_mode_valid",
        ),
        Index("ix_paper_trading_session_strategy", "strategy_id", created_at.desc()),
    )

    def __repr__(self) -> str:
        return f"<PyhronPaperTradingSession {self.name!r} status={self.status}>"


class PyhronPaperNavSnapshot(Base):
    """NAV snapshot for equity curve plotting.

    Converted to a TimescaleDB hypertable on ``timestamp``.
    """

    __tablename__ = "pyhron_paper_nav_snapshot"

    session_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("pyhron_paper_trading_session.id", ondelete="CASCADE"),
        nullable=False,
    )
    timestamp: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), nullable=False)
    nav_idr: Mapped[Decimal] = mapped_column(Numeric(20, 2), nullable=False)
    cash_idr: Mapped[Decimal] = mapped_column(Numeric(20, 2), nullable=False)
    gross_exposure_idr: Mapped[Decimal] = mapped_column(Numeric(20, 2), nullable=False)
    drawdown_pct: Mapped[Decimal] = mapped_column(Numeric(8, 4), nullable=False)
    daily_pnl_idr: Mapped[Decimal] = mapped_column(Numeric(20, 2), nullable=False)
    daily_return_pct: Mapped[Decimal] = mapped_column(Numeric(10, 6), nullable=False)

    session = relationship("PyhronPaperTradingSession", back_populates="nav_snapshots", lazy="selectin")

    __table_args__ = (
        PrimaryKeyConstraint("session_id", "timestamp"),
        Index("ix_paper_nav_snapshot_session", "session_id", timestamp.desc()),
    )

    def __repr__(self) -> str:
        return f"<PyhronPaperNavSnapshot session={self.session_id} nav={self.nav_idr}>"


class PyhronPaperPnlAttribution(Base):
    """Per-symbol daily P&L attribution for a paper trading session."""

    __tablename__ = "pyhron_paper_pnl_attribution"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("pyhron_paper_trading_session.id", ondelete="CASCADE"),
        nullable=False,
    )
    symbol: Mapped[str] = mapped_column(String(20), nullable=False)
    date: Mapped[date] = mapped_column(Date, nullable=False)
    realized_pnl_idr: Mapped[Decimal] = mapped_column(Numeric(20, 2), nullable=False, default=Decimal("0"))
    unrealized_pnl_idr: Mapped[Decimal] = mapped_column(Numeric(20, 2), nullable=False, default=Decimal("0"))
    commission_idr: Mapped[Decimal] = mapped_column(Numeric(20, 2), nullable=False, default=Decimal("0"))
    turnover_idr: Mapped[Decimal] = mapped_column(Numeric(20, 2), nullable=False, default=Decimal("0"))
    trades_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    signal_source: Mapped[str | None] = mapped_column(String(50))
    alpha_score: Mapped[Decimal | None] = mapped_column(Numeric(10, 6))
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), server_default="now()")

    session = relationship("PyhronPaperTradingSession", back_populates="pnl_attributions", lazy="selectin")

    __table_args__ = (
        UniqueConstraint("session_id", "symbol", "date", name="uq_paper_pnl_session_symbol_date"),
        Index("ix_paper_pnl_attribution_session_date", "session_id", date.desc()),
    )

    def __repr__(self) -> str:
        return f"<PyhronPaperPnlAttribution {self.symbol} {self.date}>"
