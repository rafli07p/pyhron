"""Indonesia news ticker extraction engine.

Links news articles to IDX ticker symbols using regex pattern matching
and lightweight NLP heuristics. Supports both direct ticker mentions
(e.g. "BBCA") and company name resolution from a configurable alias map.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from sqlalchemy import text

from shared.async_database_session import get_session
from shared.structured_json_logger import get_logger

logger = get_logger(__name__)

# Regex for standard IDX 4-letter ticker symbols
IDX_TICKER_PATTERN: re.Pattern[str] = re.compile(r"\b([A-Z]{4})\b")

# Common Indonesian company name aliases to ticker mappings
# Extended at runtime from the instruments table
DEFAULT_COMPANY_ALIASES: dict[str, str] = {
    "Bank Central Asia": "BBCA",
    "Bank Rakyat Indonesia": "BBRI",
    "Bank Mandiri": "BMRI",
    "Bank Negara Indonesia": "BBNI",
    "Telkom Indonesia": "TLKM",
    "Telkomsel": "TLKM",
    "Astra International": "ASII",
    "Unilever Indonesia": "UNVR",
    "Indofood": "INDF",
    "Gudang Garam": "GGRM",
    "GoTo": "GOTO",
    "Bukalapak": "BUKA",
}


@dataclass(frozen=True)
class TickerMatch:
    """A single ticker extraction match from an article.

    Attributes:
        symbol: The IDX ticker symbol (e.g. "BBCA").
        match_type: How the ticker was identified ("direct" or "alias").
        matched_text: The original text that matched.
        start_position: Character offset of the match in the source text.
        confidence: Confidence score from 0.0 to 1.0.
    """

    symbol: str
    match_type: str
    matched_text: str
    start_position: int
    confidence: float


@dataclass
class ExtractionResult:
    """Result of ticker extraction from a single article.

    Attributes:
        article_url: URL of the processed article.
        tickers: Deduplicated list of matched ticker symbols.
        matches: Detailed list of all individual matches.
        total_candidates: Number of candidate patterns found before filtering.
    """

    article_url: str
    tickers: list[str] = field(default_factory=list)
    matches: list[TickerMatch] = field(default_factory=list)
    total_candidates: int = 0


class IndonesiaNewsTickerExtractor:
    """Extracts and links IDX ticker symbols from Indonesian news articles.

    Uses a two-pass approach:
      1. **Direct match**: Regex scan for 4-letter uppercase tokens matching
         known IDX symbols loaded from the instruments table.
      2. **Alias match**: Scans for known company name aliases (both default
         and database-loaded) and maps them to their ticker symbols.

    Usage::

        extractor = IndonesiaNewsTickerExtractor()
        await extractor.initialize()
        result = extractor.extract("Bank Central Asia (BBCA) naik 2%")
        print(result.tickers)  # ["BBCA"]
    """

    def __init__(self) -> None:
        self._known_symbols: set[str] = set()
        self._company_aliases: dict[str, str] = dict(DEFAULT_COMPANY_ALIASES)
        self._alias_pattern: re.Pattern[str] | None = None
        self._initialized: bool = False

    async def initialize(self) -> None:
        """Load known symbols and company aliases from the database.

        Must be called before ``extract()`` to populate the symbol list
        and compile the alias regex pattern.
        """
        await self._load_symbols()
        await self._load_company_aliases()
        self._compile_alias_pattern()
        self._initialized = True
        logger.info(
            "ticker_extractor_initialized",
            known_symbols=len(self._known_symbols),
            company_aliases=len(self._company_aliases),
        )

    async def _load_symbols(self) -> None:
        """Load active instrument symbols from the database."""
        async with get_session() as session:
            result = await session.execute(text("SELECT symbol FROM instruments WHERE is_active = true"))
            self._known_symbols = {row[0] for row in result.fetchall()}

    async def _load_company_aliases(self) -> None:
        """Load company name to ticker mappings from the database.

        Supplements the default alias map with entries from the
        ``instrument_aliases`` table if it exists.
        """
        try:
            async with get_session() as session:
                result = await session.execute(
                    text("SELECT alias_name, symbol FROM instrument_aliases WHERE is_active = true")
                )
                for row in result.fetchall():
                    self._company_aliases[row[0]] = row[1]
        except Exception:
            logger.debug(
                "instrument_aliases_table_not_available",
                message="Using default company aliases only",
            )

    def _compile_alias_pattern(self) -> None:
        """Compile a regex pattern from all known company aliases.

        The pattern matches any of the alias names (case-insensitive)
        as whole words in the text.
        """
        if not self._company_aliases:
            self._alias_pattern = None
            return

        # Sort by length descending so longer names match first
        sorted_aliases = sorted(self._company_aliases.keys(), key=len, reverse=True)
        escaped = [re.escape(alias) for alias in sorted_aliases]
        pattern_str = r"\b(" + "|".join(escaped) + r")\b"
        self._alias_pattern = re.compile(pattern_str, re.IGNORECASE)

    def extract(self, text_content: str, article_url: str = "") -> ExtractionResult:
        """Extract IDX ticker symbols from article text.

        Runs both direct ticker matching and company alias matching,
        deduplicates results, and returns a structured extraction result.

        Args:
            text_content: The article title + body text to scan.
            article_url: Optional URL for result tracking.

        Returns:
            An ExtractionResult with matched tickers and detailed match info.
        """
        result = ExtractionResult(article_url=article_url)
        seen_symbols: set[str] = set()

        # Pass 1: Direct ticker symbol matching
        direct_matches = IDX_TICKER_PATTERN.finditer(text_content)
        for match in direct_matches:
            candidate = match.group(1)
            result.total_candidates += 1
            if candidate in self._known_symbols and candidate not in seen_symbols:
                ticker_match = TickerMatch(
                    symbol=candidate,
                    match_type="direct",
                    matched_text=candidate,
                    start_position=match.start(),
                    confidence=1.0,
                )
                result.matches.append(ticker_match)
                seen_symbols.add(candidate)

        # Pass 2: Company alias matching
        if self._alias_pattern is not None:
            alias_matches = self._alias_pattern.finditer(text_content)
            for match in alias_matches:
                matched_text = match.group(0)
                # Look up the alias (case-insensitive)
                symbol: str | None = None
                for alias, sym in self._company_aliases.items():
                    if alias.lower() == matched_text.lower():
                        symbol = sym
                        break

                if symbol is not None and symbol not in seen_symbols:
                    ticker_match = TickerMatch(
                        symbol=symbol,
                        match_type="alias",
                        matched_text=matched_text,
                        start_position=match.start(),
                        confidence=0.85,
                    )
                    result.matches.append(ticker_match)
                    seen_symbols.add(symbol)

        result.tickers = sorted(seen_symbols)
        return result

    async def extract_and_update(self, article_url: str, text_content: str) -> ExtractionResult:
        """Extract tickers and update the article record in the database.

        Convenience method that combines extraction with a database update
        to set the ``mentioned_tickers`` column on the news article.

        Args:
            article_url: URL of the article to update.
            text_content: Article text to scan for tickers.

        Returns:
            The ExtractionResult from the extraction.
        """
        result = self.extract(text_content, article_url=article_url)

        if result.tickers:
            tickers_sql = "{" + ",".join(result.tickers) + "}"
            async with get_session() as session:
                await session.execute(
                    text("UPDATE news_articles SET mentioned_tickers = :tickers::varchar[] WHERE url = :url"),
                    {"tickers": tickers_sql, "url": article_url},
                )

            logger.info(
                "tickers_extracted_and_updated",
                article_url=article_url,
                tickers=result.tickers,
                match_count=len(result.matches),
            )

        return result
