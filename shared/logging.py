"""Structured JSON logging for all Pyhron services.

Every service must use ``get_logger(__name__)`` — no ``print()`` anywhere.
Output is JSON in production, human-readable in development.

Usage::

    from shared.logging import get_logger

    logger = get_logger(__name__)
    logger.info("order_submitted", order_id=order_id, symbol=symbol)
"""

from __future__ import annotations

import logging
import os
import sys

import structlog


def _configure_structlog() -> None:
    """Configure structlog once at import time."""
    is_dev = os.environ.get("APP_ENV", "development") == "development"

    shared_processors: list[structlog.types.Processor] = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_log_level,
        structlog.stdlib.add_logger_name,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.UnicodeDecoder(),
    ]

    if is_dev:
        renderer: structlog.types.Processor = structlog.dev.ConsoleRenderer()
    else:
        renderer = structlog.processors.JSONRenderer()

    structlog.configure(
        processors=[
            *shared_processors,
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ],
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(
        structlog.stdlib.ProcessorFormatter(
            processors=[
                structlog.stdlib.ProcessorFormatter.remove_processors_meta,
                renderer,
            ],
        )
    )

    root_logger = logging.getLogger()
    root_logger.handlers.clear()
    root_logger.addHandler(handler)
    root_logger.setLevel(os.environ.get("LOG_LEVEL", "INFO").upper())

    # Quiet noisy third-party loggers
    for name in ("aiokafka", "kafka", "asyncio", "urllib3"):
        logging.getLogger(name).setLevel(logging.WARNING)


_configure_structlog()


def get_logger(name: str) -> structlog.stdlib.BoundLogger:
    """Return a named structured logger."""
    return structlog.stdlib.get_logger(name)
