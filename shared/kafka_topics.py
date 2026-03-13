"""Single source of truth for all Kafka topic names.

Never hardcode topic strings elsewhere — always reference this module.
"""


class KafkaTopic:
    """Canonical Kafka topic names for the Pyhron data pipeline."""

    # Data platform
    RAW_EOD_OHLCV = "pyhron.raw.eod_ohlcv"
    VALIDATED_EOD_OHLCV = "pyhron.validated.eod_ohlcv"
    RAW_FUNDAMENTALS = "pyhron.raw.fundamentals"
    VALIDATED_FUNDAMENTALS = "pyhron.validated.fundamentals"
    CORPORATE_ACTIONS = "pyhron.raw.corporate_actions"
    INSTRUMENT_UNIVERSE = "pyhron.raw.instrument_universe"
    MACRO_INDICATORS = "pyhron.raw.macro_indicators"
    COMMODITY_PRICES = "pyhron.raw.commodity_prices"
    NEWS_ARTICLES = "pyhron.raw.news_articles"

    # Order lifecycle
    ORDER_SUBMITTED = "pyhron.orders.order_submitted"
    ORDER_FILLED = "pyhron.orders.order_filled"

    # Portfolio
    POSITION_UPDATED = "pyhron.portfolio.position_updated"

    # Strategy signals
    MOMENTUM_SIGNALS = "pyhron.strategy.signals.momentum"
    ML_SIGNALS = "pyhron.strategy.signals.ml"

    # Paper trading
    PAPER_SESSION_STARTED = "pyhron.paper.session_started"
    PAPER_SESSION_STOPPED = "pyhron.paper.session_stopped"
    PAPER_NAV_SNAPSHOT = "pyhron.paper.nav_snapshot"
    PAPER_REBALANCE_RESULT = "pyhron.paper.rebalance_result"

    # Dead-letter queues
    DLQ_EOD_OHLCV = "pyhron.dlq.eod_ohlcv"
    DLQ_FUNDAMENTALS = "pyhron.dlq.fundamentals"
    DLQ_CORPORATE_ACTIONS = "pyhron.dlq.corporate_actions"
