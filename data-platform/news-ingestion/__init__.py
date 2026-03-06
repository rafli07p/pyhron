"""
News ingestion engine for the Enthropy data platform.

Fetches news articles from Polygon.io's reference news API, stores
them with basic sentiment scores, and provides search/retrieval with
tenant isolation.
"""

from __future__ import annotations

import hashlib
import uuid
from datetime import date, datetime, timezone
from typing import Optional, Sequence

import structlog
from polygon import RESTClient as PolygonClient
from sqlalchemy import (
    DateTime,
    Float,
    Index,
    String,
    Text,
    UniqueConstraint,
    select,
    text,
    or_,
)
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, UUID as PG_UUID
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

logger = structlog.get_logger(__name__)


# ---------------------------------------------------------------------------
# Base & ORM
# ---------------------------------------------------------------------------

class Base(DeclarativeBase):
    pass


class NewsArticle(Base):
    """Stored news article with sentiment metadata."""

    __tablename__ = "news_articles"
    __table_args__ = (
        UniqueConstraint("tenant_id", "article_hash", name="uq_news_article"),
        Index("ix_news_published", "tenant_id", "published_utc"),
        Index("ix_news_symbols", "tenant_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    tenant_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    article_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    author: Mapped[Optional[str]] = mapped_column(String(256), nullable=True)
    source_name: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    source_url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    article_url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    image_url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    symbols: Mapped[Optional[list]] = mapped_column(ARRAY(String), nullable=True)
    keywords: Mapped[Optional[list]] = mapped_column(ARRAY(String), nullable=True)
    published_utc: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Sentiment
    sentiment_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    sentiment_label: Mapped[Optional[str]] = mapped_column(String(16), nullable=True)

    # Raw JSON from the API for future re-processing
    raw_data: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )


# ---------------------------------------------------------------------------
# Sentiment helper
# ---------------------------------------------------------------------------

def _compute_basic_sentiment(title: str, description: Optional[str] = None) -> tuple[float, str]:
    """Naive keyword-based sentiment scorer (placeholder for a real NLP model).

    Returns ``(score, label)`` where score is in ``[-1.0, 1.0]`` and
    label is ``positive``, ``negative``, or ``neutral``.
    """
    combined = (title + " " + (description or "")).lower()

    positive_words = {
        "surge", "gain", "rally", "record", "profit", "beat", "upgrade",
        "growth", "bullish", "outperform", "strong", "positive", "up",
        "higher", "boost", "jump", "soar", "improve",
    }
    negative_words = {
        "crash", "plunge", "loss", "miss", "downgrade", "bearish", "cut",
        "decline", "drop", "fall", "weak", "negative", "down", "lower",
        "slump", "warning", "risk", "fear", "concern", "recession",
    }

    pos = sum(1 for w in positive_words if w in combined)
    neg = sum(1 for w in negative_words if w in combined)
    total = pos + neg
    if total == 0:
        return 0.0, "neutral"

    score = (pos - neg) / total
    if score > 0.15:
        return round(score, 4), "positive"
    elif score < -0.15:
        return round(score, 4), "negative"
    return round(score, 4), "neutral"


# ---------------------------------------------------------------------------
# NewsIngestionEngine
# ---------------------------------------------------------------------------

class NewsIngestionEngine:
    """Fetch, score, store, and search news articles from Polygon.io.

    Parameters
    ----------
    polygon_api_key : str
        Polygon.io API key.
    database_url : str
        Async SQLAlchemy connection string.
    tenant_id : str
        Multi-tenancy identifier.
    """

    def __init__(
        self,
        polygon_api_key: str,
        database_url: str = "postgresql+asyncpg://localhost/enthropy",
        tenant_id: str = "default",
    ) -> None:
        self.tenant_id = tenant_id
        self._log = logger.bind(tenant_id=tenant_id, component="NewsIngestionEngine")
        self._polygon = PolygonClient(api_key=polygon_api_key)
        self._engine = create_async_engine(
            database_url, pool_size=5, max_overflow=10, pool_pre_ping=True,
        )
        self._session_factory = async_sessionmaker(self._engine, expire_on_commit=False)
        self._log.info("news_ingestion_engine_initialised")

    async def init_schema(self) -> None:
        async with self._engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        self._log.info("news_schema_initialised")

    async def close(self) -> None:
        await self._engine.dispose()

    # ------------------------------------------------------------------
    # Fetch from Polygon
    # ------------------------------------------------------------------

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, max=30),
        retry=retry_if_exception_type((OSError, ConnectionError, TimeoutError)),
        reraise=True,
    )
    async def fetch_news(
        self,
        *,
        symbol: Optional[str] = None,
        limit: int = 100,
        published_utc_gte: Optional[str] = None,
        published_utc_lte: Optional[str] = None,
        order: str = "desc",
    ) -> list[dict]:
        """Fetch news from Polygon and persist to the database.

        Parameters
        ----------
        symbol : str | None
            Ticker to filter by (optional).
        limit : int
            Max articles to fetch per call (Polygon caps at 1000).
        published_utc_gte / published_utc_lte : str | None
            ISO-8601 datetime bounds.
        order : str
            ``"asc"`` or ``"desc"`` by published date.

        Returns
        -------
        list[dict]
            Stored article dicts.
        """
        import asyncio

        params: dict = {"limit": min(limit, 1000), "order": order}
        if symbol:
            params["ticker"] = symbol.upper()
        if published_utc_gte:
            params["published_utc.gte"] = published_utc_gte
        if published_utc_lte:
            params["published_utc.lte"] = published_utc_lte

        raw_articles = await asyncio.to_thread(self._fetch_polygon_news, params)
        stored = await self._store_articles(raw_articles)
        self._log.info("news_fetched_and_stored", requested=limit, stored=len(stored))
        return stored

    def _fetch_polygon_news(self, params: dict) -> list[dict]:
        articles = []
        for article in self._polygon.list_ticker_news(**params):
            tickers = []
            if hasattr(article, "tickers") and article.tickers:
                tickers = list(article.tickers)

            pub_utc = getattr(article, "published_utc", None)
            if isinstance(pub_utc, str):
                try:
                    pub_utc = datetime.fromisoformat(pub_utc.replace("Z", "+00:00"))
                except ValueError:
                    pub_utc = None

            publisher = getattr(article, "publisher", None)
            source_name = None
            source_url = None
            if publisher:
                source_name = getattr(publisher, "name", None)
                source_url = getattr(publisher, "homepage_url", None)

            articles.append({
                "title": article.title,
                "author": getattr(article, "author", None),
                "source_name": source_name,
                "source_url": source_url,
                "article_url": getattr(article, "article_url", None),
                "image_url": getattr(article, "image_url", None),
                "description": getattr(article, "description", None),
                "symbols": tickers,
                "keywords": getattr(article, "keywords", None),
                "published_utc": pub_utc,
                "raw": {
                    "id": getattr(article, "id", None),
                    "title": article.title,
                    "amp_url": getattr(article, "amp_url", None),
                },
            })
        return articles

    # ------------------------------------------------------------------
    # Store
    # ------------------------------------------------------------------

    async def _store_articles(self, raw_articles: list[dict]) -> list[dict]:
        stored: list[dict] = []
        async with self._session_factory() as session:
            async with session.begin():
                for a in raw_articles:
                    # Deduplicate via content hash
                    hash_input = f"{a['title']}|{a.get('article_url', '')}"
                    article_hash = hashlib.sha256(hash_input.encode()).hexdigest()

                    existing = (
                        await session.execute(
                            select(NewsArticle).where(
                                NewsArticle.tenant_id == self.tenant_id,
                                NewsArticle.article_hash == article_hash,
                            )
                        )
                    ).scalar_one_or_none()
                    if existing:
                        continue

                    score, label = _compute_basic_sentiment(
                        a["title"], a.get("description")
                    )

                    record = NewsArticle(
                        tenant_id=self.tenant_id,
                        article_hash=article_hash,
                        title=a["title"],
                        author=a.get("author"),
                        source_name=a.get("source_name"),
                        source_url=a.get("source_url"),
                        article_url=a.get("article_url"),
                        image_url=a.get("image_url"),
                        description=a.get("description"),
                        symbols=a.get("symbols"),
                        keywords=a.get("keywords"),
                        published_utc=a.get("published_utc"),
                        sentiment_score=score,
                        sentiment_label=label,
                        raw_data=a.get("raw"),
                    )
                    session.add(record)
                    stored.append(self._article_to_dict(record))

        return stored

    # ------------------------------------------------------------------
    # Search / query
    # ------------------------------------------------------------------

    async def search_news(
        self,
        *,
        query: Optional[str] = None,
        symbol: Optional[str] = None,
        sentiment: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[dict]:
        """Search stored news articles with flexible filtering.

        Parameters
        ----------
        query : str | None
            Free-text search in title/description.
        symbol : str | None
            Filter articles mentioning this ticker.
        sentiment : str | None
            Filter by sentiment label (positive, negative, neutral).
        start_date / end_date : datetime | None
            Published-date bounds.
        limit / offset : int
            Pagination.
        """
        stmt = (
            select(NewsArticle)
            .where(NewsArticle.tenant_id == self.tenant_id)
        )

        if query:
            pattern = f"%{query}%"
            stmt = stmt.where(
                or_(
                    NewsArticle.title.ilike(pattern),
                    NewsArticle.description.ilike(pattern),
                )
            )
        if symbol:
            stmt = stmt.where(NewsArticle.symbols.any(symbol.upper()))
        if sentiment:
            stmt = stmt.where(NewsArticle.sentiment_label == sentiment.lower())
        if start_date:
            stmt = stmt.where(NewsArticle.published_utc >= start_date)
        if end_date:
            stmt = stmt.where(NewsArticle.published_utc <= end_date)

        stmt = (
            stmt.order_by(NewsArticle.published_utc.desc())
            .offset(offset)
            .limit(limit)
        )

        async with self._session_factory() as session:
            result = await session.execute(stmt)
            rows = result.scalars().all()

        articles = [self._article_to_dict(r) for r in rows]
        self._log.debug("news_searched", count=len(articles), query=query, symbol=symbol)
        return articles

    async def get_news_for_symbol(
        self,
        symbol: str,
        *,
        limit: int = 50,
    ) -> list[dict]:
        """Convenience wrapper: get latest news for a specific symbol."""
        return await self.search_news(symbol=symbol, limit=limit)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _article_to_dict(article: NewsArticle) -> dict:
        return {
            "id": str(article.id),
            "title": article.title,
            "author": article.author,
            "source_name": article.source_name,
            "article_url": article.article_url,
            "description": article.description,
            "symbols": article.symbols,
            "keywords": article.keywords,
            "published_utc": (
                article.published_utc.isoformat() if article.published_utc else None
            ),
            "sentiment_score": article.sentiment_score,
            "sentiment_label": article.sentiment_label,
        }


__all__ = [
    "NewsArticle",
    "NewsIngestionEngine",
]
