"""Pyhron Indonesia financial news ingestion pipeline.

Modules:
    aggregator: RSS feed aggregation from Indonesian sources.
    ticker_extractor: Link news articles to IDX ticker symbols.
    sentiment: IndoBERT-based multilingual sentiment scoring.
"""

from data_platform.news_ingestion.aggregator import IndonesiaFinancialNewsAggregator
from data_platform.news_ingestion.sentiment import IndonesiaNewsSentimentScorer
from data_platform.news_ingestion.ticker_extractor import IndonesiaNewsTickerExtractor

__all__: list[str] = [
    "IndonesiaFinancialNewsAggregator",
    "IndonesiaNewsSentimentScorer",
    "IndonesiaNewsTickerExtractor",
]
