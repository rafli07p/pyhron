"""Strategy configuration model.

Persists strategy definitions, hyperparameters, risk configuration, and
the instrument universe for each trading strategy.
"""

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import Boolean, ForeignKey, Index, String
from sqlalchemy.dialects.postgresql import JSONB, TIMESTAMP, UUID
from sqlalchemy.orm import Mapped, mapped_column

from shared.async_database_session import Base


class Strategy(Base):
    """Trading strategy configuration record.

    Attributes:
        id: UUID primary key.
        user_id: Owner of the strategy.
        name: Human-readable strategy name.
        strategy_type: Category (momentum, mean_reversion, ml_signal, pairs).
        parameters: JSONB hyperparameters.
        is_active: Whether the strategy is enabled.
        is_live: True for live trading, False for paper.
        universe: JSONB list of symbols this strategy trades.
        risk_config: JSONB risk limits (max_position_pct, max_drawdown_pct, etc.).
        created_at: Row creation timestamp.
        updated_at: Row last-update timestamp.
    """

    __tablename__ = "strategies"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    strategy_type: Mapped[str] = mapped_column(String(50), nullable=False)
    parameters: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    is_live: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    universe: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    risk_config: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), server_default="now()")
    updated_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), server_default="now()")

    __table_args__ = (Index("ix_strategies_user_created", "user_id", created_at.desc()),)
