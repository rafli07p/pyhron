"""CLI entrypoint for the strategy signal Kafka consumer.

Usage::

    python -m services.paper_trading.strategy_signal_consumer
    python -m services.paper_trading.strategy_signal_consumer --batch-size 100 --timeout 10
"""

from __future__ import annotations

import argparse
import asyncio
import signal
import sys

from shared.structured_json_logger import get_logger

logger = get_logger(__name__)


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Pyhron strategy signal Kafka consumer for paper trading",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=50,
        help="Max signals per batch before flushing (default: 50)",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=5.0,
        help="Max seconds before flushing a partial batch (default: 5.0)",
    )
    return parser.parse_args()


async def _run(batch_size: int, batch_timeout_s: float) -> None:
    from services.paper_trading.strategy_signal_consumer import (
        StrategySignalKafkaConsumer,
    )

    consumer = StrategySignalKafkaConsumer(
        batch_size=batch_size,
        batch_timeout_s=batch_timeout_s,
    )

    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, lambda: asyncio.create_task(_shutdown(consumer)))

    await consumer.start()
    try:
        await consumer.run()
    finally:
        await consumer.stop()


async def _shutdown(consumer: object) -> None:
    logger.info("shutdown_signal_received")
    if hasattr(consumer, "stop"):
        await consumer.stop()
    sys.exit(0)


def main() -> None:
    args = _parse_args()
    logger.info(
        "strategy_signal_consumer_starting",
        batch_size=args.batch_size,
        timeout=args.timeout,
    )
    asyncio.run(_run(args.batch_size, args.timeout))


if __name__ == "__main__":
    main()
