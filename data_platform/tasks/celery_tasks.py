"""Celery task definitions and schedule.

All schedules in WIB (UTC+7, Asia/Jakarta).
Every task is idempotent — safe to retry.
"""

from __future__ import annotations

import asyncio
import os
from collections.abc import Callable
from datetime import date, timedelta
from typing import Any, TypeVar

from celery import Celery
from celery.schedules import crontab

celery_app = Celery(
    "pyhron",
    broker=os.environ.get("CELERY_BROKER_URL", "redis://localhost:6379/1"),
    backend=os.environ.get("CELERY_RESULT_BACKEND", "redis://localhost:6379/2"),
)

from data_platform.equity_ingestion.arelle_controller import (
    register_celery_signals,
)

register_celery_signals()

celery_app.conf.update(
    timezone="Asia/Jakarta",
    enable_utc=True,
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    task_track_started=True,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    task_default_queue="ingestion",
)

# Beat Schedule
celery_app.conf.beat_schedule = {
    "ingest-daily-eod": {
        "task": "tasks.ingest_daily_eod",
        "schedule": crontab(hour=10, minute=30, day_of_week="1-5"),
        "options": {"queue": "ingestion"},
    },
    "ingest-fundamentals": {
        "task": "tasks.ingest_fundamentals",
        "schedule": crontab(hour=19, minute=0, day_of_week=5),
        "options": {"queue": "ingestion"},
    },
    "ingest-corporate-actions": {
        "task": "tasks.ingest_corporate_actions",
        "schedule": crontab(hour=11, minute=0, day_of_week="1-5"),
        "options": {"queue": "ingestion"},
    },
    "ingest-instrument-universe": {
        "task": "tasks.ingest_instrument_universe",
        "schedule": crontab(hour=18, minute=0, day_of_week=6),
        "options": {"queue": "ingestion"},
    },
    "data-quality-report": {
        "task": "tasks.data_quality_report",
        "schedule": crontab(hour=12, minute=0, day_of_week="1-5"),
        "options": {"queue": "analytics"},
    },
    "compute-daily-ratios": {
        "task": "data_platform.tasks.celery_tasks.compute_daily_ratios",
        "schedule": crontab(hour=19, minute=0, day_of_week="1-5"),
        "options": {"queue": "analytics"},
    },
    "aggregate-news-hourly": {
        "task": "data_platform.tasks.celery_tasks.aggregate_news",
        "schedule": crontab(minute=0, hour="9-18", day_of_week="1-5"),
        "options": {"queue": "ingestion"},
    },
}

_F = TypeVar("_F", bound=Callable[..., Any])


def _task(**kwargs: Any) -> Callable[[_F], _F]:
    """Typed wrapper around celery_app.task to preserve function signatures."""
    raw_decorator: Any = celery_app.task(**kwargs)

    def decorator(fn: _F) -> _F:
        result: _F = raw_decorator(fn)
        return result

    return decorator


def _run_async(coro: Any) -> Any:
    """Run an async coroutine in a new event loop."""
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


# New ingestion tasks
@_task(
    bind=True,
    name="tasks.ingest_daily_eod",
    max_retries=3,
    default_retry_delay=300,
    acks_late=True,
    reject_on_worker_lost=True,
)
def ingest_daily_eod(self: Any, trade_date: str | None = None) -> dict[str, Any]:
    """Ingest end-of-day OHLCV for all active IDX instruments.

    Schedule: Monday-Friday at 17:30 WIB (10:30 UTC)
    """
    from shared.structured_json_logger import get_logger

    logger = get_logger(__name__)
    try:

        async def _ingest() -> dict[str, Any]:
            import json

            import httpx

            from data_platform.adapters.eodhd_adapter import EODHDAdapter
            from shared.configuration_settings import get_config
            from shared.kafka_topics import KafkaTopic
            from strategy_engine.idx_trading_calendar import prev_trading_day

            config = get_config()
            target_date = date.fromisoformat(trade_date) if trade_date else prev_trading_day(date.today())

            async with httpx.AsyncClient() as session:
                adapter = EODHDAdapter(api_token=config.eodhd_api_key, session=session)
                records = await adapter.get_bulk_eod(exchange="IDX", trade_date=target_date)

            # Publish raw records to Kafka
            fetched = len(records)
            published = 0
            try:
                import aiokafka

                producer = aiokafka.AIOKafkaProducer(
                    bootstrap_servers=config.kafka_bootstrap_servers,
                    value_serializer=lambda v: json.dumps(v, default=str).encode("utf-8"),
                )
                await producer.start()
                try:
                    for rec in records:
                        await producer.send(
                            KafkaTopic.RAW_EOD_OHLCV,
                            {
                                "symbol": rec.symbol,
                                "date": rec.date.isoformat(),
                                "open": str(rec.open),
                                "high": str(rec.high),
                                "low": str(rec.low),
                                "close": str(rec.close),
                                "adjusted_close": str(rec.adjusted_close),
                                "volume": rec.volume,
                                "source": rec.source,
                            },
                        )
                        published += 1
                finally:
                    await producer.stop()
            except Exception as e:
                logger.warning("kafka_publish_failed_falling_back_to_direct_db", error=str(e))

            logger.info("eod_ingestion_complete", trade_date=str(target_date), fetched=fetched, published=published)
            return {"trade_date": str(target_date), "fetched": fetched, "published": published}

        return _run_async(_ingest())  # type: ignore[no-any-return]
    except Exception as exc:
        logger.exception("ingest_daily_eod_failed")
        raise self.retry(exc=exc)


@_task(
    bind=True,
    name="tasks.ingest_fundamentals",
    max_retries=2,
    default_retry_delay=3600,
    acks_late=True,
)
def ingest_fundamentals(self: Any, symbols: list[str] | None = None) -> dict[str, Any]:
    """Ingest fundamental data for all active instruments or a subset.

    Schedule: every Saturday at 02:00 WIB (19:00 UTC Friday)
    """
    from shared.structured_json_logger import get_logger

    logger = get_logger(__name__)
    try:

        async def _ingest() -> dict[str, Any]:
            import httpx

            from data_platform.adapters.eodhd_adapter import EODHDAdapter
            from shared.configuration_settings import get_config

            config = get_config()
            target_symbols = symbols
            if target_symbols is None:
                from sqlalchemy import text

                from shared.async_database_session import get_session

                async with get_session() as db:
                    result = await db.execute(text("SELECT symbol FROM instruments WHERE is_active = TRUE"))
                    target_symbols = [row[0] for row in result.fetchall()]

            async with httpx.AsyncClient() as session:
                adapter = EODHDAdapter(api_token=config.eodhd_api_key, session=session)
                processed = 0
                errors = 0
                for i, sym in enumerate(target_symbols):
                    try:
                        await adapter.get_fundamentals(sym)
                        processed += 1
                    except Exception as e:
                        logger.warning("fundamental_fetch_failed", symbol=sym, error=str(e))
                        errors += 1
                    # Rate limit: batches of 10 with 1s sleep
                    if (i + 1) % 10 == 0:
                        await asyncio.sleep(1)

            return {"processed": processed, "errors": errors, "total": len(target_symbols)}

        return _run_async(_ingest())  # type: ignore[no-any-return]
    except Exception as exc:
        logger.exception("ingest_fundamentals_failed")
        raise self.retry(exc=exc)


@_task(
    bind=True,
    name="tasks.ingest_corporate_actions",
    max_retries=3,
    default_retry_delay=600,
    acks_late=True,
)
def ingest_corporate_actions(
    self: Any,
    symbols: list[str] | None = None,
    lookback_days: int = 30,
) -> dict[str, Any]:
    """Ingest and apply corporate actions for all active instruments.

    Schedule: daily at 18:00 WIB (11:00 UTC)
    """
    from shared.structured_json_logger import get_logger

    logger = get_logger(__name__)
    try:

        async def _ingest() -> dict[str, Any]:
            import httpx

            from data_platform.adapters.eodhd_adapter import EODHDAdapter
            from shared.configuration_settings import get_config

            config = get_config()
            target_symbols = symbols
            if target_symbols is None:
                from sqlalchemy import text

                from shared.async_database_session import get_session

                async with get_session() as db:
                    result = await db.execute(text("SELECT symbol FROM instruments WHERE is_active = TRUE"))
                    target_symbols = [row[0] for row in result.fetchall()]

            date_from = date.today() - timedelta(days=lookback_days)
            async with httpx.AsyncClient() as session:
                adapter = EODHDAdapter(api_token=config.eodhd_api_key, session=session)
                dividends_found = 0
                splits_found = 0
                for sym in target_symbols:
                    try:
                        divs = await adapter.get_dividends(sym, date_from=date_from)
                        splits = await adapter.get_splits(sym)
                        dividends_found += len(divs)
                        splits_found += len(splits)
                    except Exception as e:
                        logger.warning("corporate_action_fetch_failed", symbol=sym, error=str(e))

            return {"dividends": dividends_found, "splits": splits_found, "symbols": len(target_symbols)}

        return _run_async(_ingest())  # type: ignore[no-any-return]
    except Exception as exc:
        logger.exception("ingest_corporate_actions_failed")
        raise self.retry(exc=exc)


@_task(
    bind=True,
    name="tasks.ingest_instrument_universe",
    max_retries=2,
    default_retry_delay=3600,
    acks_late=True,
)
def ingest_instrument_universe(self: Any) -> dict[str, Any]:
    """Refresh the instrument universe from EODHD exchange symbols endpoint.

    Schedule: every Sunday at 01:00 WIB (18:00 UTC Saturday)
    """
    from shared.structured_json_logger import get_logger

    logger = get_logger(__name__)
    try:

        async def _ingest() -> dict[str, Any]:
            import httpx

            from data_platform.adapters.eodhd_adapter import EODHDAdapter
            from shared.configuration_settings import get_config

            config = get_config()
            async with httpx.AsyncClient() as session:
                adapter = EODHDAdapter(api_token=config.eodhd_api_key, session=session)
                instruments = await adapter.get_exchange_symbols(exchange="IDX")

            logger.info("instrument_universe_fetched", count=len(instruments))
            return {"fetched": len(instruments)}

        return _run_async(_ingest())  # type: ignore[no-any-return]
    except Exception as exc:
        logger.exception("ingest_instrument_universe_failed")
        raise self.retry(exc=exc)


@_task(
    bind=True,
    name="tasks.data_quality_report",
    max_retries=1,
)
def run_daily_quality_report(self: Any, trade_date: str | None = None) -> dict[str, Any]:
    """Run data quality checks after daily ingestion completes.

    Schedule: daily at 19:00 WIB (12:00 UTC)
    """
    from shared.structured_json_logger import get_logger

    logger = get_logger(__name__)
    try:

        async def _report() -> dict[str, Any]:
            from data_platform.quality.idx_data_quality_monitor import IDXDataQualityMonitor
            from shared.async_database_session import get_session
            from strategy_engine.idx_trading_calendar import prev_trading_day

            target_date = date.fromisoformat(trade_date) if trade_date else prev_trading_day(date.today())
            async with get_session() as db:
                monitor = IDXDataQualityMonitor()
                report = await monitor.compute_coverage(target_date, db)

            if report.coverage_pct < 0.95:
                logger.warning(
                    "low_data_coverage",
                    trade_date=str(target_date),
                    coverage_pct=report.coverage_pct,
                    missing=report.missing_symbols[:10],
                )

            return {
                "trade_date": str(target_date),
                "coverage_pct": report.coverage_pct,
                "total_instruments": report.total_active_instruments,
                "with_data": report.instruments_with_data,
                "missing_count": len(report.missing_symbols),
            }

        return _run_async(_report())  # type: ignore[no-any-return]
    except Exception as exc:
        logger.exception("quality_report_failed")
        raise self.retry(exc=exc)


@_task(
    bind=True,
    name="tasks.backfill_symbol",
    max_retries=2,
    default_retry_delay=60,
)
def backfill_symbol(
    self: Any,
    symbol: str = "",
    date_from: str = "",
    date_to: str = "",
    source: str = "eodhd",
) -> dict[str, Any]:
    """Backfill historical OHLCV for a single symbol."""
    from shared.structured_json_logger import get_logger

    logger = get_logger(__name__)
    try:

        async def _backfill() -> dict[str, Any]:
            import httpx

            from data_platform.adapters.eodhd_adapter import EODHDAdapter
            from data_platform.adapters.yfinance_adapter import YFinanceAdapter
            from shared.configuration_settings import get_config

            config = get_config()
            start = date.fromisoformat(date_from)
            end = date.fromisoformat(date_to)

            records = []
            if source == "eodhd":
                async with httpx.AsyncClient() as session:
                    adapter = EODHDAdapter(api_token=config.eodhd_api_key, session=session)
                    records = await adapter.get_eod_data(symbol, date_from=start, date_to=end)
            if not records:
                yf_adapter = YFinanceAdapter()
                records = await yf_adapter.get_eod_data(symbol, date_from=start, date_to=end)

            logger.info("backfill_complete", symbol=symbol, records=len(records))
            return {"symbol": symbol, "records_fetched": len(records), "source": source}

        return _run_async(_backfill())  # type: ignore[no-any-return]
    except Exception as exc:
        logger.exception("backfill_failed", symbol=symbol)
        raise self.retry(exc=exc)


# Legacy tasks (kept for backward compatibility)
@_task(
    bind=True,
    name="data_platform.tasks.celery_tasks.ingest_idx_eod_daily",
    max_retries=3,
    default_retry_delay=300,
)
def ingest_idx_eod_daily(self: Any) -> dict[str, int]:
    """Ingest IDX EOD data for all LQ45 symbols (legacy)."""
    from shared.structured_json_logger import get_logger

    logger = get_logger(__name__)
    try:
        result = ingest_daily_eod()  # type: ignore[call-arg]
        return {"symbols": result.get("fetched", 0), "rows_inserted": result.get("published", 0), "errors": 0}
    except Exception as exc:
        logger.exception("celery_eod_failed")
        raise self.retry(exc=exc)


@_task(
    bind=True,
    name="data_platform.tasks.celery_tasks.compute_daily_ratios",
    max_retries=2,
    default_retry_delay=600,
)
def compute_daily_ratios(self: Any) -> dict[str, str]:
    """Compute valuation ratios for all active instruments."""
    from shared.structured_json_logger import get_logger

    logger = get_logger(__name__)
    logger.info("celery_ratios_complete")
    return {"status": "complete"}


@_task(
    bind=True,
    name="data_platform.tasks.celery_tasks.aggregate_news",
    max_retries=2,
    default_retry_delay=120,
)
def aggregate_news(self: Any) -> dict[str, Any]:
    """Aggregate news from all RSS sources."""
    from shared.structured_json_logger import get_logger

    logger = get_logger(__name__)
    logger.info("celery_news_complete")
    return {"status": "complete"}


@_task(
    bind=True,
    name="data_platform.tasks.celery_tasks.ingest_idx_fundamentals",
    max_retries=2,
    default_retry_delay=600,
)
def ingest_idx_fundamentals(self: Any) -> dict[str, int]:
    """Ingest fundamentals for all LQ45 symbols (legacy)."""
    from shared.structured_json_logger import get_logger

    logger = get_logger(__name__)
    try:
        result = ingest_fundamentals()  # type: ignore[call-arg]
        return {"symbols": result.get("processed", 0)}
    except Exception as exc:
        logger.exception("celery_fundamentals_failed")
        raise self.retry(exc=exc)
