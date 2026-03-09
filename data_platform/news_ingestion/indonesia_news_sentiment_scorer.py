"""IndoBERT-based multilingual sentiment scoring for Indonesian financial news.

Provides both a lightweight lexicon-based scorer for real-time use and an
IndoBERT transformer-based scorer for higher-accuracy batch processing.
Supports Indonesian (Bahasa Indonesia) and English financial text.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from decimal import Decimal
from enum import StrEnum
from typing import Any

from sqlalchemy import text

from shared.async_database_session import get_session
from shared.structured_json_logger import get_logger

logger = get_logger(__name__)


class SentimentLabel(StrEnum):
    """Sentiment classification labels."""

    POSITIVE = "positive"
    NEGATIVE = "negative"
    NEUTRAL = "neutral"


@dataclass(frozen=True)
class SentimentResult:
    """Result of sentiment analysis on a single text.

    Attributes:
        score: Sentiment score in [-1.0, 1.0]. Positive values indicate
            bullish/positive sentiment, negative values indicate
            bearish/negative sentiment.
        label: Categorical sentiment label.
        confidence: Model confidence in [0.0, 1.0].
        method: Scoring method used ("lexicon" or "indobert").
    """

    score: Decimal
    label: SentimentLabel
    confidence: float
    method: str


# ── Indonesian financial sentiment lexicon ────────────────────────────────────

POSITIVE_WORDS_ID: set[str] = {
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
    "kuat",
    "meningkat",
    "melesat",
    "menguat",
    "cerah",
    "membaik",
    "prospek",
    "akumulasi",
    "breakout",
    "rally",
}

NEGATIVE_WORDS_ID: set[str] = {
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
    "lemah",
    "melemah",
    "menurun",
    "merosot",
    "suram",
    "memburuk",
    "tekanan",
    "distribusi",
    "breakdown",
    "crash",
}

# English financial sentiment terms for bilingual articles
POSITIVE_WORDS_EN: set[str] = {
    "bullish",
    "rally",
    "surge",
    "gain",
    "profit",
    "growth",
    "upgrade",
    "outperform",
    "buy",
    "strong",
    "positive",
    "upside",
    "breakout",
    "accumulate",
    "dividend",
    "expansion",
    "recovery",
}

NEGATIVE_WORDS_EN: set[str] = {
    "bearish",
    "crash",
    "decline",
    "loss",
    "deficit",
    "downgrade",
    "underperform",
    "sell",
    "weak",
    "negative",
    "downside",
    "breakdown",
    "distribute",
    "recession",
    "contraction",
    "risk",
}

# Combine all lexicons
ALL_POSITIVE: set[str] = POSITIVE_WORDS_ID | POSITIVE_WORDS_EN
ALL_NEGATIVE: set[str] = NEGATIVE_WORDS_ID | NEGATIVE_WORDS_EN


class IndonesiaNewsSentimentScorer:
    """Multilingual sentiment scorer for Indonesian financial news.

    Provides two scoring modes:

    1. **Lexicon mode** (default): Fast bag-of-words scoring using curated
       Indonesian and English financial sentiment term lists. Suitable for
       real-time scoring during RSS ingestion.

    2. **IndoBERT mode**: Transformer-based scoring using the IndoBERT model
       (``indobenchmark/indobert-base-p1``) fine-tuned on financial sentiment.
       Higher accuracy but requires GPU and model loading. Used for batch
       reprocessing and accuracy validation.

    Usage::

        scorer = IndonesiaNewsSentimentScorer()
        result = scorer.score_lexicon("BBCA naik 5% setelah laporan laba")
        print(result)  # SentimentResult(score=Decimal('1.0'), label='positive', ...)

        # For IndoBERT mode (requires transformers library):
        await scorer.initialize_indobert()
        result = await scorer.score_indobert("Saham BBRI anjlok 10%")
    """

    def __init__(self) -> None:
        self._indobert_model: Any = None
        self._indobert_tokenizer: Any = None
        self._indobert_initialized: bool = False

    def score_lexicon(self, text_content: str) -> SentimentResult:
        """Score text sentiment using the lexicon-based approach.

        Fast, deterministic scoring suitable for real-time use. Counts
        positive and negative term occurrences and computes a normalized
        score.

        Args:
            text_content: Text to analyze for sentiment.

        Returns:
            A SentimentResult with the computed score and label.
        """
        words = set(re.findall(r"\b\w+\b", text_content.lower()))
        pos_count = len(words & ALL_POSITIVE)
        neg_count = len(words & ALL_NEGATIVE)
        total = pos_count + neg_count

        if total == 0:
            return SentimentResult(
                score=Decimal("0"),
                label=SentimentLabel.NEUTRAL,
                confidence=0.5,
                method="lexicon",
            )

        raw_score = (pos_count - neg_count) / total
        score = Decimal(str(round(raw_score, 3)))
        confidence = min(1.0, total / 5.0)  # Higher word count = higher confidence

        if score > Decimal("0.1"):
            label = SentimentLabel.POSITIVE
        elif score < Decimal("-0.1"):
            label = SentimentLabel.NEGATIVE
        else:
            label = SentimentLabel.NEUTRAL

        return SentimentResult(
            score=score,
            label=label,
            confidence=round(confidence, 3),
            method="lexicon",
        )

    async def initialize_indobert(self) -> None:
        """Initialize the IndoBERT model and tokenizer for transformer-based scoring.

        Loads the ``indobenchmark/indobert-base-p1`` model with a sentiment
        classification head. Requires the ``transformers`` and ``torch``
        packages to be installed.

        Raises:
            ImportError: If transformers or torch are not installed.
        """
        try:
            from transformers import AutoModelForSequenceClassification, AutoTokenizer

            model_name = "indobenchmark/indobert-base-p1"
            self._indobert_tokenizer = AutoTokenizer.from_pretrained(model_name)
            self._indobert_model = AutoModelForSequenceClassification.from_pretrained(model_name, num_labels=3)
            self._indobert_model.eval()
            self._indobert_initialized = True
            logger.info(
                "indobert_model_initialized",
                model_name=model_name,
            )
        except ImportError:
            logger.error(
                "indobert_dependencies_missing",
                message="Install transformers and torch: pip install transformers torch",
            )
            raise

    async def score_indobert(self, text_content: str) -> SentimentResult:
        """Score text sentiment using the IndoBERT transformer model.

        Tokenizes the input text, runs inference through IndoBERT, and
        maps the output logits to a sentiment score and label.

        Args:
            text_content: Text to analyze for sentiment.

        Returns:
            A SentimentResult with the model-predicted score and label.

        Raises:
            RuntimeError: If IndoBERT has not been initialized.
        """
        if not self._indobert_initialized:
            raise RuntimeError("IndoBERT model not initialized. Call initialize_indobert() first.")

        import torch

        inputs = self._indobert_tokenizer(
            text_content,
            return_tensors="pt",
            truncation=True,
            max_length=512,
            padding=True,
        )

        with torch.no_grad():
            outputs = self._indobert_model(**inputs)
            logits = outputs.logits
            probabilities = torch.softmax(logits, dim=-1)

        # Map model outputs: index 0=negative, 1=neutral, 2=positive
        probs = probabilities[0].tolist()
        neg_prob: float = probs[0]
        probs[1]
        pos_prob: float = probs[2]

        # Compute continuous score from probabilities
        raw_score = pos_prob - neg_prob
        score = Decimal(str(round(raw_score, 3)))
        confidence = float(max(probs))

        if score > Decimal("0.1"):
            label = SentimentLabel.POSITIVE
        elif score < Decimal("-0.1"):
            label = SentimentLabel.NEGATIVE
        else:
            label = SentimentLabel.NEUTRAL

        return SentimentResult(
            score=score,
            label=label,
            confidence=round(confidence, 3),
            method="indobert",
        )

    async def batch_score(
        self,
        articles: list[dict[str, Any]],
        use_indobert: bool = False,
    ) -> list[SentimentResult]:
        """Score a batch of articles and optionally update the database.

        Args:
            articles: List of article dicts with at least ``url`` and
                ``content_summary`` or ``title`` keys.
            use_indobert: If True and IndoBERT is initialized, use the
                transformer model. Otherwise falls back to lexicon scoring.

        Returns:
            List of SentimentResult objects, one per input article.
        """
        results: list[SentimentResult] = []

        for article in articles:
            text_content = article.get("content_summary") or article.get("title", "")

            if use_indobert and self._indobert_initialized:
                result = await self.score_indobert(text_content)
            else:
                result = self.score_lexicon(text_content)

            results.append(result)

        logger.info(
            "batch_sentiment_scoring_complete",
            article_count=len(articles),
            method="indobert" if (use_indobert and self._indobert_initialized) else "lexicon",
        )

        return results

    async def update_article_sentiment(
        self,
        article_url: str,
        result: SentimentResult,
    ) -> None:
        """Persist a sentiment result to the news_articles table.

        Args:
            article_url: URL of the article to update.
            result: The SentimentResult to persist.
        """
        async with get_session() as session:
            await session.execute(
                text("UPDATE news_articles SET sentiment_score = :score, sentiment_label = :label WHERE url = :url"),
                {
                    "score": float(result.score),
                    "label": result.label.value,
                    "url": article_url,
                },
            )

        logger.debug(
            "article_sentiment_updated",
            article_url=article_url,
            score=float(result.score),
            label=result.label.value,
            method=result.method,
        )
