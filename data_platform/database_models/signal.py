"""Trading signal model.

Captures strategy-generated trading signals with strength, timing, and
metadata for audit and backtesting analysis.  Designed as a TimescaleDB
hypertable partitioned by ``generated_at``.
"""

import enum
import uuid
from datetime import datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import Boolean, ForeignKey, Index, Numeric, String, text
from sqlalchemy.dialects.postgresql import ENUM, JSONB, TIMESTAMP, UUID
from sqlalchemy.orm import Mapped, mapped_column

from shared.async_database_session import Base


class SignalType(enum.StrEnum):
    """Trading signal direction."""

    ENTRY_LONG = "entry_long"
    ENTRY_SHORT = "entry_short"
    EXIT_LONG = "exit_long"
    EXIT_SHORT = "exit_short"
    REBALANCE = "rebalance"


class Signal(Base):
    """Strategy-generated trading signal.

    Attributes:
        id: UUID primary key.
        strategy_id: FK to originating strategy.
        instrument_symbol: Ticker symbol of the target instrument.
        signal_type: Direction/action of the signal.
        strength: Normalised signal strength in [-1.0, 1.0].
        bar_timestamp: The bar that generated the signal.
        generated_at: Wall-clock time of signal generation (hypertable partition key).
        acted_on: Whether an order was placed from this signal.
        resulting_order_id: Client order ID if acted upon.
        metadata_json: Raw feature values, model scores, etc.
    """

    __tablename__ = "signals"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=text("uuid_generate_v4()"),
    )
    strategy_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("strategies.id", ondelete="CASCADE"),
        nullable=False,
    )
    instrument_symbol: Mapped[str] = mapped_column(String(20), nullable=False)
    signal_type: Mapped[SignalType] = mapped_column(
        ENUM(SignalType, name="signal_type", create_type=False),
        nullable=False,
    )
    strength: Mapped[Decimal] = mapped_column(Numeric(5, 4), nullable=False)
    bar_timestamp: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), nullable=False)
    generated_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), nullable=False, server_default="now()")
    acted_on: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    resulting_order_id: Mapped[str | None] = mapped_column(String(36))
    metadata_json: Mapped[dict[str, Any] | None] = mapped_column(JSONB)

    __table_args__ = (
        Index(
            "ix_signals_strategy_bar_ts",
            "strategy_id",
            bar_timestamp.desc(),
        ),
        Index("ix_signals_instrument_generated", "instrument_symbol", "generated_at"),
    )
