"""Indonesia financial news aggregation from RSS feeds.

Aggregates articles from major Indonesian financial news sources, extracts
mentioned IDX tickers, scores sentiment, and persists results to the database.

RSS sources:
  - Bisnis Indonesia
  - Kontan
  - CNBC Indonesia
  - Okezone Finance
"""

from __future__ import annotations

import re
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any
from xml.etree import ElementTree

import httpx
from sqlalchemy import text

from shared.async_database_session import get_session
from shared.structured_json_logger import get_logger

logger = get_logger(__name__)

RSS_SOURCES: dict[str, str] = {
    "Bisnis Indonesia": "https://www.bisnis.com/feed",
    "Kontan": "https://www.kontan.co.id/rss/investasi",
    "CNBC Indonesia": "https://www.cnbcindonesia.com/rss",
    "Okezone Finance": "https://economy.okezone.com/rss",
}

# Simple Indonesian financial sentiment lexicon
POSITIVE_WORDS: set[str] = {
    "naik",
    "untung",
    "laba",
    "tumbuh",
    "positif",
    "surplus",
    "bullish",
    "melonjak",
    "rekor",
    "ekspansi",
    "dividen",
    "optimis",
}
NEGATIVE_WORDS: set[str] = {
    "turun",
    "rugi",
    "defisit",
    "negatif",
    "bearish",
    "anjlok",
    "jatuh",
    "koreksi",
    "resesi",
    "gagal",
    "pesimis",
    "bangkrut",
}

# Default HTTP timeout for RSS fetches
RSS_FETCH_TIMEOUT_SECONDS: float = 15.0


def simple_sentiment(text_content: str) -> tuple[Decimal, str]:
    """Compute lexicon-based sentiment score for Indonesian financial text.

    Uses a bag-of-words approach against curated positive and negative
    Indonesian financial term lists.

    Args:
        text_content: Raw text content to score.

    Returns:
        A tuple of (score, label) where score is a Decimal in [-1, 1]
        and label is one of "positive", "negative", or "neutral".
    """
    words = set(text_content.lower().split())
    pos = len(words & POSITIVE_WORDS)
    neg = len(words & NEGATIVE_WORDS)
    total = pos + neg
    if total == 0:
        return Decimal("0"), "neutral"
    score = Decimal(str(round((pos - neg) / total, 3)))
    if score > Decimal("0.1"):
        return score, "positive"
    if score < Decimal("-0.1"):
        return score, "negative"
    return score, "neutral"


class IndonesiaFinancialNewsAggregator:
    """Aggregates Indonesian financial news from RSS feeds.

    Fetches articles from configured RSS sources, extracts mentioned IDX
    ticker symbols, scores sentiment using a lexicon-based approach, and
    persists new articles to the database with deduplication by URL.

    Usage::

        aggregator = IndonesiaFinancialNewsAggregator()
        result = await aggregator.aggregate()
        print(result)  # {"new_articles": 12, "skipped": 3}
    """

    def __init__(self) -> None:
        self._known_symbols: set[str] = set()

    async def _load_symbols(self) -> None:
        """Load known active instrument symbols from the database."""
        async with get_session() as session:
            result = await session.execute(text("SELECT symbol FROM instruments WHERE is_active = true"))
            self._known_symbols = {row[0] for row in result.fetchall()}

    async def aggregate(self) -> dict[str, int]:
        """Fetch and process all configured RSS sources.

        Loads the current instrument symbol list, then iterates over each
        RSS source to fetch, parse, score, and store articles.

        Returns:
            A dict with ``new_articles`` and ``skipped`` counts.
        """
        await self._load_symbols()
        total_new = 0
        total_skipped = 0

        for source_name, url in RSS_SOURCES.items():
            try:
                articles = await self._fetch_rss(source_name, url)
                for article in articles:
                    is_new = await self._store_article(article)
                    if is_new:
                        total_new += 1
                    else:
                        total_skipped += 1
            except Exception:
                logger.exception("rss_fetch_failed", source=source_name)

        logger.info("news_aggregation_complete", new=total_new, skipped=total_skipped)
        return {"new_articles": total_new, "skipped": total_skipped}

    async def _fetch_rss(self, source: str, url: str) -> list[dict[str, Any]]:
        """Parse an RSS feed and return a list of article dicts.

        Args:
            source: Human-readable source name (e.g. "Bisnis Indonesia").
            url: The RSS feed URL.

        Returns:
            List of article dicts with title, url, source, published_at,
            content_summary, sentiment_score, sentiment_label, and
            mentioned_tickers.
        """
        articles: list[dict[str, Any]] = []
        try:
            async with httpx.AsyncClient(timeout=RSS_FETCH_TIMEOUT_SECONDS) as client:
                resp = await client.get(url)
                resp.raise_for_status()

            root = ElementTree.fromstring(resp.text)
            for item in root.iter("item"):
                title_el = item.find("title")
                link_el = item.find("link")
                pub_date_el = item.find("pubDate")
                desc_el = item.find("description")

                if title_el is None or link_el is None:
                    continue

                title = title_el.text or ""
                link = link_el.text or ""
                description = desc_el.text or "" if desc_el is not None else ""

                # Extract tickers
                full_text = f"{title} {description}"
                tickers = self._extract_tickers(full_text)

                # Sentiment
                score, label = simple_sentiment(full_text)

                articles.append(
                    {
                        "title": title.strip(),
                        "url": link.strip(),
                        "source": source,
                        "published_at": pub_date_el.text if pub_date_el is not None else None,
                        "content_summary": description[:500] if description else None,
                        "sentiment_score": score,
                        "sentiment_label": label,
                        "mentioned_tickers": tickers,
                    }
                )
        except httpx.RequestError:
            logger.exception("rss_connection_failed", source=source)

        return articles

    def _extract_tickers(self, text_content: str) -> list[str]:
        """Extract known IDX ticker symbols from text.

        Matches uppercase 4-letter words (IDX ticker format) and filters
        against the loaded instrument symbol list.

        Args:
            text_content: Text to scan for ticker mentions.

        Returns:
            Sorted list of matched ticker symbols.
        """
        candidates = set(re.findall(r"\b[A-Z]{4}\b", text_content))
        return sorted(candidates & self._known_symbols)

    async def _store_article(self, article: dict[str, Any]) -> bool:
        """Store an article in the database with URL-based deduplication.

        Args:
            article: Article dict from ``_fetch_rss``.

        Returns:
            True if the article was newly inserted, False if it was a
            duplicate (already exists by URL).
        """
        async with get_session() as session:
            # Check for duplicate URL
            existing = await session.execute(
                text("SELECT 1 FROM news_articles WHERE url = :url"),
                {"url": article["url"]},
            )
            if existing.fetchone():
                return False

            tickers = article["mentioned_tickers"]
            tickers_sql = "{" + ",".join(tickers) + "}" if tickers else "{}"

            await session.execute(
                text("""
                    INSERT INTO news_articles (
                        id, title, url, source, published_at,
                        content_summary, sentiment_score, sentiment_label,
                        mentioned_tickers
                    ) VALUES (
                        uuid_generate_v4(), :title, :url, :source, :published_at,
                        :summary, :score, :label, :tickers::varchar[]
                    )
                """),
                {
                    "title": article["title"],
                    "url": article["url"],
                    "source": article["source"],
                    "published_at": article.get("published_at") or datetime.now(tz=UTC).isoformat(),
                    "summary": article.get("content_summary"),
                    "score": float(article["sentiment_score"]),
                    "label": article["sentiment_label"],
                    "tickers": tickers_sql,
                },
            )
            return True
