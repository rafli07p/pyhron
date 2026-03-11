"""IDX equity news articles with NLP sentiment annotations.

Aggregates news articles mentioning IDX equities and enriches them with
sentiment scores, labels, and mentioned ticker extraction.
"""

from __future__ import annotations

import enum
import uuid
from typing import TYPE_CHECKING

from sqlalchemy import (
    CheckConstraint,
    Enum,
    Index,
    Numeric,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import ARRAY, TIMESTAMP, UUID
from sqlalchemy.orm import Mapped, mapped_column

from shared.async_database_session import Base

if TYPE_CHECKING:
    from datetime import datetime
    from decimal import Decimal


class SentimentLabel(enum.StrEnum):
    """NLP sentiment classification."""

    POSITIVE = "positive"
    NEGATIVE = "negative"
    NEUTRAL = "neutral"


class IdxEquityNewsArticle(Base):
    """News article with NLP sentiment annotations.

    Attributes:
        id: Primary key (UUID).
        title: Article headline.
        url: Canonical article URL (unique).
        source: Publisher or feed name.
        published_at: Original publication timestamp.
        content_summary: Short summary or lead paragraph.
        full_content: Full article text (when available).
        sentiment_score: Continuous sentiment score in ``[-1, 1]``.
        sentiment_label: Discrete sentiment label.
        sentiment_model: Model name/version used for scoring.
        mentioned_tickers: Array of ticker symbols mentioned.
        created_at: Row creation timestamp.
    """

    __tablename__ = "news_articles"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    url: Mapped[str] = mapped_column(Text, unique=True, nullable=False)
    source: Mapped[str | None] = mapped_column(String(100))
    published_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), nullable=False)
    content_summary: Mapped[str | None] = mapped_column(Text)
    full_content: Mapped[str | None] = mapped_column(Text)
    sentiment_score: Mapped[Decimal | None] = mapped_column(Numeric(4, 3))
    sentiment_label: Mapped[SentimentLabel | None] = mapped_column(Enum(SentimentLabel, name="sentiment_label_enum"))
    sentiment_model: Mapped[str | None] = mapped_column(String(100))
    mentioned_tickers: Mapped[list[str] | None] = mapped_column(ARRAY(String(20)), server_default="{}")
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), server_default="now()")

    __table_args__ = (
        Index("ix_idx_equity_news_articles_published_at", published_at.desc()),
        Index(
            "ix_idx_equity_news_articles_tickers",
            "mentioned_tickers",
            postgresql_using="gin",
        ),
        CheckConstraint(
            "sentiment_score IS NULL OR (sentiment_score BETWEEN -1 AND 1)",
            name="sentiment_range",
        ),
    )
