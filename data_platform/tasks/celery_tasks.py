"""Celery task definitions and schedule.

All schedules in WIB (UTC+7, Asia/Jakarta).
Every task is idempotent — safe to retry.
"""

from __future__ import annotations

import asyncio
import os
from collections.abc import Callable
from typing import Any, TypeVar

from celery import Celery
from celery.schedules import crontab

celery_app = Celery(
    "pyhron",
    broker=os.environ.get("CELERY_BROKER_URL", "redis://localhost:6379/1"),
    backend=os.environ.get("CELERY_RESULT_BACKEND", "redis://localhost:6379/2"),
)

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

# ── Beat Schedule ───────────────────────────────────────────────────────────

celery_app.conf.beat_schedule = {
    "ingest-idx-eod-daily": {
        "task": "data_platform.tasks.celery_tasks.ingest_idx_eod_daily",
        "schedule": crontab(hour=16, minute=30, day_of_week="1-5"),
        "options": {"queue": "ingestion"},
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
    "ingest-idx-fundamentals-weekly": {
        "task": "data_platform.tasks.celery_tasks.ingest_idx_fundamentals",
        "schedule": crontab(hour=2, minute=0, day_of_week="0"),
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


@_task(
    bind=True,
    name="data_platform.tasks.celery_tasks.ingest_idx_eod_daily",
    max_retries=3,
    default_retry_delay=300,
)
def ingest_idx_eod_daily(self: Any) -> dict[str, int]:
    """Ingest IDX EOD data for all LQ45 symbols."""
    from shared.structured_json_logger import get_logger

    logger = get_logger(__name__)
    try:
        from data_platform.ingestion.idx_eod import IDXEODIngester

        ingester: Any = IDXEODIngester()
        results: Any = _run_async(ingester.ingest_all())
        total_inserted = sum(r.rows_inserted for r in results)
        total_errors = sum(len(r.errors) for r in results)
        logger.info(
            "celery_eod_complete",
            symbols=len(results),
            rows_inserted=total_inserted,
            errors=total_errors,
        )
        return {"symbols": len(results), "rows_inserted": total_inserted, "errors": total_errors}
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
    try:
        from data_platform.ingestion.idx_fundamentals import IDXFundamentalsIngester

        ingester: Any = IDXFundamentalsIngester()

        async def _compute() -> None:
            from data_platform.ingestion.idx_eod import IDX_LQ45_SYMBOLS

            for sym in IDX_LQ45_SYMBOLS:
                try:
                    await ingester._compute_ratios(sym)
                except Exception:
                    logger.exception("ratio_computation_failed", symbol=sym)

        _run_async(_compute())
        logger.info("celery_ratios_complete")
        return {"status": "complete"}
    except Exception as exc:
        logger.exception("celery_ratios_failed")
        raise self.retry(exc=exc)


@_task(
    bind=True,
    name="data_platform.tasks.celery_tasks.aggregate_news",
    max_retries=2,
    default_retry_delay=120,
)
def aggregate_news(self: Any) -> Any:
    """Aggregate news from all RSS sources."""
    from shared.structured_json_logger import get_logger

    logger = get_logger(__name__)
    try:
        from data_platform.ingestion.news_aggregator import NewsAggregator

        aggregator: Any = NewsAggregator()
        result: Any = _run_async(aggregator.aggregate())
        logger.info("celery_news_complete", **result)
        return result
    except Exception as exc:
        logger.exception("celery_news_failed")
        raise self.retry(exc=exc)


@_task(
    bind=True,
    name="data_platform.tasks.celery_tasks.ingest_idx_fundamentals",
    max_retries=2,
    default_retry_delay=600,
)
def ingest_idx_fundamentals(self: Any) -> dict[str, int]:
    """Ingest fundamentals for all LQ45 symbols."""
    from shared.structured_json_logger import get_logger

    logger = get_logger(__name__)
    try:
        from data_platform.ingestion.idx_eod import IDX_LQ45_SYMBOLS
        from data_platform.ingestion.idx_fundamentals import IDXFundamentalsIngester

        ingester: Any = IDXFundamentalsIngester()

        async def _ingest() -> list[Any]:
            results: list[Any] = []
            for sym in IDX_LQ45_SYMBOLS:
                try:
                    r = await ingester.ingest_symbol(sym)
                    results.append(r)
                except Exception:
                    logger.exception("fundamentals_failed", symbol=sym)
            return results

        results = _run_async(_ingest())
        logger.info("celery_fundamentals_complete", symbols=len(results))
        return {"symbols": len(results)}
    except Exception as exc:
        logger.exception("celery_fundamentals_failed")
        raise self.retry(exc=exc)
