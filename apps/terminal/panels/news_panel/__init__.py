"""News Panel for the Enthropy Terminal.

Displays market news with sentiment analysis, symbol filtering, and
search capabilities. Integrates with external news feeds and the
Enthropy data pipeline.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum
from typing import Any, Optional

logger = logging.getLogger(__name__)


class SentimentLabel(StrEnum):
    """News sentiment classification."""

    POSITIVE = "POSITIVE"
    NEGATIVE = "NEGATIVE"
    NEUTRAL = "NEUTRAL"
    MIXED = "MIXED"


@dataclass
class NewsArticle:
    """A single news article with metadata and sentiment."""

    article_id: str = ""
    title: str = ""
    summary: str = ""
    source: str = ""
    url: str = ""
    published_at: datetime | None = None
    symbols: list[str] = field(default_factory=list)
    sentiment: SentimentLabel = SentimentLabel.NEUTRAL
    sentiment_score: float = 0.0
    categories: list[str] = field(default_factory=list)


class NewsPanel:
    """Display market news with sentiment filtering.

    Fetches and renders market news articles filtered by symbol,
    query terms, or sentiment label. Supports real-time streaming
    of breaking news events.

    Parameters
    ----------
    data_client:
        Instance of ``apps.terminal.data_client.DataClient`` for
        fetching news data. If ``None``, operates in offline mode.
    """

    def __init__(self, data_client: Any = None) -> None:
        self._data_client = data_client
        self._articles: list[NewsArticle] = []
        self._current_symbol: str | None = None
        logger.info("NewsPanel initialized")

    @property
    def article_count(self) -> int:
        """Number of loaded articles."""
        return len(self._articles)

    async def render_news(self, symbol: str | None = None, limit: int = 50) -> dict[str, Any]:
        """Render news articles for a given symbol.

        Parameters
        ----------
        symbol:
            Instrument symbol to filter news by. If ``None``, fetches
            general market news.
        limit:
            Maximum number of articles to return.

        Returns
        -------
        dict[str, Any]
            News feed payload with articles and metadata.
        """
        self._current_symbol = symbol

        if self._data_client is not None:
            try:
                raw = await self._data_client.get_market_data(
                    symbol=symbol or "",
                    data_type="news",
                    limit=limit,
                )
                if isinstance(raw, list):
                    self._articles = [self._parse_article(a) for a in raw]
            except Exception as exc:
                logger.error("Failed to fetch news for %s: %s", symbol, exc)

        filtered = self._articles[:limit]
        logger.info("Rendered %d news articles for %s", len(filtered), symbol or "market")
        return {
            "symbol": symbol,
            "articles": [self._serialize_article(a) for a in filtered],
            "total_count": len(filtered),
        }

    async def search_news(self, query: str, limit: int = 25) -> list[dict[str, Any]]:
        """Search news articles by query string.

        Parameters
        ----------
        query:
            Free-text search query.
        limit:
            Maximum number of results.

        Returns
        -------
        list[dict[str, Any]]
            Matching articles.
        """
        query_lower = query.lower()
        matches = [a for a in self._articles if query_lower in a.title.lower() or query_lower in a.summary.lower()]

        if self._data_client is not None and not matches:
            try:
                raw = await self._data_client.get_market_data(
                    symbol="",
                    data_type="news_search",
                    query=query,
                    limit=limit,
                )
                if isinstance(raw, list):
                    matches = [self._parse_article(a) for a in raw]
            except Exception as exc:
                logger.error("News search failed for query '%s': %s", query, exc)

        results = matches[:limit]
        logger.info("Search '%s' returned %d results", query, len(results))
        return [self._serialize_article(a) for a in results]

    def filter_by_sentiment(self, sentiment: str) -> list[dict[str, Any]]:
        """Filter loaded articles by sentiment label.

        Parameters
        ----------
        sentiment:
            One of ``POSITIVE``, ``NEGATIVE``, ``NEUTRAL``, ``MIXED``.

        Returns
        -------
        list[dict[str, Any]]
            Articles matching the sentiment filter.
        """
        target = SentimentLabel(sentiment.upper())
        filtered = [a for a in self._articles if a.sentiment == target]
        logger.info("Filtered %d articles with sentiment=%s", len(filtered), target)
        return [self._serialize_article(a) for a in filtered]

    @staticmethod
    def _parse_article(raw: dict[str, Any]) -> NewsArticle:
        """Parse a raw article dictionary into a NewsArticle."""
        return NewsArticle(
            article_id=raw.get("id", raw.get("article_id", "")),
            title=raw.get("title", ""),
            summary=raw.get("summary", raw.get("description", "")),
            source=raw.get("source", ""),
            url=raw.get("url", ""),
            published_at=datetime.fromisoformat(raw["published_at"]) if "published_at" in raw else None,
            symbols=raw.get("symbols", []),
            sentiment=SentimentLabel(raw.get("sentiment", "NEUTRAL").upper()),
            sentiment_score=float(raw.get("sentiment_score", 0.0)),
            categories=raw.get("categories", []),
        )

    @staticmethod
    def _serialize_article(article: NewsArticle) -> dict[str, Any]:
        """Serialize a NewsArticle for rendering."""
        return {
            "article_id": article.article_id,
            "title": article.title,
            "summary": article.summary,
            "source": article.source,
            "url": article.url,
            "published_at": article.published_at.isoformat() if article.published_at else None,
            "symbols": article.symbols,
            "sentiment": article.sentiment.value,
            "sentiment_score": article.sentiment_score,
            "categories": article.categories,
        }


__all__ = [
    "NewsArticle",
    "NewsPanel",
    "SentimentLabel",
]
