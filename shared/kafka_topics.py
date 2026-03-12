"""Single source of truth for all Kafka topic names.

Never hardcode topic strings elsewhere — always reference this module.
"""


class KafkaTopic:
    """Canonical Kafka topic names for the Pyhron data pipeline."""

    RAW_EOD_OHLCV = "pyhron.raw.eod_ohlcv"
    VALIDATED_EOD_OHLCV = "pyhron.validated.eod_ohlcv"
    RAW_FUNDAMENTALS = "pyhron.raw.fundamentals"
    VALIDATED_FUNDAMENTALS = "pyhron.validated.fundamentals"
    CORPORATE_ACTIONS = "pyhron.raw.corporate_actions"
    INSTRUMENT_UNIVERSE = "pyhron.raw.instrument_universe"
    MACRO_INDICATORS = "pyhron.raw.macro_indicators"
    COMMODITY_PRICES = "pyhron.raw.commodity_prices"
    NEWS_ARTICLES = "pyhron.raw.news_articles"
    DLQ_EOD_OHLCV = "pyhron.dlq.eod_ohlcv"
    DLQ_FUNDAMENTALS = "pyhron.dlq.fundamentals"
    DLQ_CORPORATE_ACTIONS = "pyhron.dlq.corporate_actions"
