"""Pyhron Indonesia financial news ingestion pipeline.

Modules:
    indonesia_financial_news_aggregator: RSS feed aggregation from Indonesian sources.
    indonesia_news_ticker_extractor: Link news articles to IDX ticker symbols.
    indonesia_news_sentiment_scorer: IndoBERT-based multilingual sentiment scoring.
"""

from data_platform.news_ingestion.indonesia_financial_news_aggregator import (
    IndonesiaFinancialNewsAggregator,
)
from data_platform.news_ingestion.indonesia_news_ticker_extractor import (
    IndonesiaNewsTickerExtractor,
)
from data_platform.news_ingestion.indonesia_news_sentiment_scorer import (
    IndonesiaNewsSentimentScorer,
)

__all__: list[str] = [
    "IndonesiaFinancialNewsAggregator",
    "IndonesiaNewsTickerExtractor",
    "IndonesiaNewsSentimentScorer",
]
