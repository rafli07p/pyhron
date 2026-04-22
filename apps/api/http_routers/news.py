"""Indonesia news sentiment API endpoints.

News aggregation with NLP-based sentiment scoring for Indonesian market
and company-specific coverage. Primary source: EODHD Financial Data API.
"""

from __future__ import annotations

import asyncio
import uuid
from datetime import UTC, date, datetime, timedelta
from functools import partial
from typing import Any

import httpx
from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field

from shared.configuration_settings import get_config
from shared.security.auth import TokenPayload
from shared.security.rbac import Role, require_role
from shared.structured_json_logger import get_logger

logger = get_logger(__name__)
router = APIRouter(prefix="/v1/news", tags=["news-sentiment"], redirect_slashes=False)

EODHD_URL = "https://eodhd.com/api/news"
DEFAULT_SYMBOLS = ["BBCA", "BBRI", "BMRI", "TLKM", "ASII"]


# Response Models
class NewsArticle(BaseModel):
    id: str
    title: str
    source: str
    url: str
    published_at: datetime
    summary: str | None = None
    sentiment_score: float | None = Field(None, ge=-1.0, le=1.0, description="Sentiment: -1 bearish to +1 bullish")
    sentiment_label: str | None = Field(None, description="bearish, neutral, bullish")
    symbols: list[str] = Field(default_factory=list)
    categories: list[str] = Field(default_factory=list)


class SentimentSummary(BaseModel):
    symbol: str
    article_count: int
    avg_sentiment: float
    sentiment_label: str
    bullish_count: int
    neutral_count: int
    bearish_count: int
    period_start: date
    period_end: date


class SentimentSummaryResponse(BaseModel):
    summaries: list[SentimentSummary]
    total_articles_analyzed: int


def _classify(polarity: float) -> str:
    if polarity >= 0.1:
        return "bullish"
    if polarity <= -0.1:
        return "bearish"
    return "neutral"


# Endpoints
@router.get("", response_model=list[NewsArticle])
async def get_news(
    symbol: str | None = Query(None, description="Filter by ticker symbol"),
    category: str | None = Query(None, description="Filter by category"),
    start_date: date | None = Query(None),
    end_date: date | None = Query(None),
    sentiment: str | None = Query(None, pattern="^(bullish|neutral|bearish)$"),
    limit: int = Query(20, ge=1, le=100),
    _user: TokenPayload = Depends(require_role(Role.VIEWER)),
) -> list[NewsArticle]:
    """Fetch news from EODHD with sentiment scores."""
    cfg = get_config()
    api_key = cfg.eodhd_api_key
    logger.info("news_queried", symbol=symbol, category=category, sentiment=sentiment)

    def _fetch() -> list[dict[str, Any]]:
        params: dict[str, Any] = {
            "api_token": api_key,
            "fmt": "json",
            "limit": limit,
        }
        if symbol:
            params["s"] = f"{symbol.upper()}.JK" if not symbol.endswith(".JK") else symbol.upper()
        if start_date:
            params["from"] = str(start_date)
        if end_date:
            params["to"] = str(end_date)
        try:
            with httpx.Client(timeout=15) as client:
                resp = client.get(EODHD_URL, params=params)
                resp.raise_for_status()
                data = resp.json()
                return data if isinstance(data, list) else []
        except Exception as exc:
            logger.warning("eodhd_news_fetch_failed", error=str(exc))
            return []

    loop = asyncio.get_event_loop()
    raw_articles = await loop.run_in_executor(None, _fetch)

    results: list[NewsArticle] = []
    for a in raw_articles:
        sent_data = a.get("sentiment", {}) or {}
        polarity = float(sent_data.get("polarity", 0) or 0)
        sent_label = _classify(polarity)

        if sentiment and sent_label != sentiment:
            continue

        symbols_raw = a.get("symbols", []) or []
        symbols_clean = [
            s.replace(".JK", "").replace(".US", "")
            for s in symbols_raw
            if isinstance(s, str)
        ]

        tags = a.get("tags", []) or []

        try:
            pub_dt = datetime.fromisoformat((a.get("date") or "").replace("Z", "+00:00"))
        except Exception:
            pub_dt = datetime.now(UTC)

        content = a.get("content")
        summary = content[:300] if isinstance(content, str) and content else None

        results.append(NewsArticle(
            id=str(uuid.uuid4()),
            title=a.get("title", ""),
            source=a.get("source", "Unknown"),
            url=a.get("url", ""),
            published_at=pub_dt,
            summary=summary,
            sentiment_score=round(polarity, 3),
            sentiment_label=sent_label,
            symbols=symbols_clean,
            categories=tags[:3] if isinstance(tags, list) else [],
        ))

    return results


@router.get("/sentiment-summary", response_model=SentimentSummaryResponse)
async def get_sentiment_summary(
    symbols: str | None = Query(None, description="Comma-separated symbols e.g. BBCA,BBRI"),
    days: int = Query(30, ge=1, le=365),
    _user: TokenPayload = Depends(require_role(Role.VIEWER)),
) -> SentimentSummaryResponse:
    """Aggregate sentiment per symbol from EODHD news."""
    cfg = get_config()
    api_key = cfg.eodhd_api_key
    symbol_list = (
        [s.strip().upper() for s in symbols.split(",") if s.strip()]
        if symbols else list(DEFAULT_SYMBOLS)
    )
    from_date = (datetime.now(UTC) - timedelta(days=days)).date()
    today = datetime.now(UTC).date()
    logger.info("sentiment_summary_queried", symbols=symbol_list, days=days)

    def _fetch_symbol(sym: str) -> list[dict[str, Any]]:
        try:
            with httpx.Client(timeout=15) as client:
                resp = client.get(EODHD_URL, params={
                    "api_token": api_key,
                    "fmt": "json",
                    "s": f"{sym}.JK",
                    "from": str(from_date),
                    "limit": 50,
                })
                resp.raise_for_status()
                data = resp.json()
                return data if isinstance(data, list) else []
        except Exception as exc:
            logger.warning("eodhd_sentiment_fetch_failed", symbol=sym, error=str(exc))
            return []

    loop = asyncio.get_event_loop()
    all_summaries: list[SentimentSummary] = []
    total = 0

    for sym in symbol_list:
        articles = await loop.run_in_executor(None, partial(_fetch_symbol, sym))
        if not articles:
            continue

        scores: list[float] = []
        bullish = neutral = bearish = 0
        for a in articles:
            sent = a.get("sentiment", {}) or {}
            p = float(sent.get("polarity", 0) or 0)
            scores.append(p)
            if p >= 0.1:
                bullish += 1
            elif p <= -0.1:
                bearish += 1
            else:
                neutral += 1

        avg = sum(scores) / len(scores) if scores else 0.0
        total += len(articles)

        all_summaries.append(SentimentSummary(
            symbol=sym,
            article_count=len(articles),
            avg_sentiment=round(avg, 3),
            sentiment_label=_classify(avg),
            bullish_count=bullish,
            neutral_count=neutral,
            bearish_count=bearish,
            period_start=from_date,
            period_end=today,
        ))

    return SentimentSummaryResponse(summaries=all_summaries, total_articles_analyzed=total)
