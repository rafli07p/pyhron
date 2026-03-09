"""IDX news aggregation with sentiment analysis.

RSS sources:
  - Bisnis Indonesia
  - Kontan
  - CNBC Indonesia
  - Okezone Economy

Ticker extraction matches against loaded Instrument.symbol list.
"""

from __future__ import annotations

import re
import uuid
from datetime import datetime, timezone
from decimal import Decimal
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
    "Okezone Economy": "https://economy.okezone.com/rss",
}

# Simple Indonesian financial sentiment lexicon
POSITIVE_WORDS = {
    "naik", "untung", "laba", "tumbuh", "positif", "surplus", "bullish",
    "melonjak", "rekor", "ekspansi", "dividen", "optimis",
}
NEGATIVE_WORDS = {
    "turun", "rugi", "defisit", "negatif", "bearish", "anjlok", "jatuh",
    "koreksi", "resesi", "gagal", "pesimis", "bangkrut",
}


def simple_sentiment(text_content: str) -> tuple[Decimal, str]:
    """Lexicon-based sentiment scoring for Indonesian financial text."""
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


class NewsAggregator:
    """Aggregates IDX news from RSS feeds with sentiment analysis."""

    def __init__(self) -> None:
        self._known_symbols: set[str] = set()

    async def _load_symbols(self) -> None:
        """Load known instrument symbols from DB."""
        async with get_session() as session:
            result = await session.execute(
                text("SELECT symbol FROM instruments WHERE is_active = true")
            )
            self._known_symbols = {row[0] for row in result.fetchall()}

    async def aggregate(self) -> dict:
        """Fetch and process all RSS sources."""
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

    async def _fetch_rss(self, source: str, url: str) -> list[dict]:
        """Parse RSS feed and return article dicts."""
        articles = []
        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
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

                articles.append({
                    "title": title.strip(),
                    "url": link.strip(),
                    "source": source,
                    "published_at": pub_date_el.text if pub_date_el is not None else None,
                    "content_summary": description[:500] if description else None,
                    "sentiment_score": score,
                    "sentiment_label": label,
                    "mentioned_tickers": tickers,
                })
        except httpx.RequestError:
            logger.exception("rss_connection_failed", source=source)

        return articles

    def _extract_tickers(self, text_content: str) -> list[str]:
        """Extract known ticker symbols from text."""
        # Match uppercase words that could be tickers
        candidates = set(re.findall(r"\b[A-Z]{4}\b", text_content))
        return sorted(candidates & self._known_symbols)

    async def _store_article(self, article: dict) -> bool:
        """Store article in DB. Returns True if new, False if duplicate."""
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
                    "published_at": article.get("published_at") or datetime.now(tz=timezone.utc).isoformat(),
                    "summary": article.get("content_summary"),
                    "score": float(article["sentiment_score"]),
                    "label": article["sentiment_label"],
                    "tickers": tickers_sql,
                },
            )
            return True
