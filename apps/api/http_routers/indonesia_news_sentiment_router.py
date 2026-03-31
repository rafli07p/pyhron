"""Indonesia news sentiment API endpoints.

News aggregation with NLP-based sentiment scoring
for Indonesian market and company-specific coverage.
"""




from datetime import date, datetime
from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field

from shared.security.auth import TokenPayload
from shared.security.rbac import Role, require_role
from shared.structured_json_logger import get_logger

logger = get_logger(__name__)
router = APIRouter(prefix="/v1/news", tags=["news-sentiment"])


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


# Endpoints
@router.get("/", response_model=list[NewsArticle])
async def get_news(
    symbol: str | None = Query(None, description="Filter by ticker symbol"),
    category: str | None = Query(None, description="Filter by category"),
    start_date: date | None = Query(None, description="Start date for date range"),
    end_date: date | None = Query(None, description="End date for date range"),
    sentiment: str | None = Query(None, pattern="^(bullish|neutral|bearish)$", description="Filter by sentiment"),
    limit: int = Query(20, ge=1, le=100),
    _user: TokenPayload = Depends(require_role(Role.VIEWER)),
) -> list[NewsArticle]:
    """Get news articles with sentiment scores, optionally filtered."""
    logger.info("news_queried", symbol=symbol, category=category)
    return []


@router.get("/sentiment-summary", response_model=SentimentSummaryResponse)
async def get_sentiment_summary(
    symbols: str | None = Query(None, description="Comma-separated symbols"),
    days: int = Query(7, ge=1, le=90, description="Lookback period in days"),
    _user: TokenPayload = Depends(require_role(Role.VIEWER)),
) -> SentimentSummaryResponse:
    """Get aggregated sentiment summary by symbol over a time period."""
    symbol_list = symbols.split(",") if symbols else []
    logger.info("sentiment_summary_queried", symbols=symbol_list, days=days)
    return SentimentSummaryResponse(summaries=[], total_articles_analyzed=0)
