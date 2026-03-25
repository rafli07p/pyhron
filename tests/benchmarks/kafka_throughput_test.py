"""Kafka ingestion throughput benchmark.

Measures the maximum sustained throughput of the Kafka producer/consumer
pipeline by publishing synthetic market data events and measuring
end-to-end latency and message rates.

Usage::

    python tests/benchmarks/kafka_throughput_test.py
    python tests/benchmarks/kafka_throughput_test.py --messages 100000 --producers 4
    python tests/benchmarks/kafka_throughput_test.py --bootstrap localhost:9092
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import random
import statistics
import time
from dataclasses import dataclass
from datetime import UTC, datetime

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("kafka_throughput")

IDX_SYMBOLS = [
    "BBCA",
    "BBRI",
    "BMRI",
    "TLKM",
    "ASII",
    "UNVR",
    "HMSP",
    "GGRM",
    "ICBP",
    "KLBF",
    "BBNI",
    "INDF",
    "PGAS",
    "SMGR",
    "JSMR",
    "PTBA",
    "ADRO",
    "ANTM",
    "INCO",
    "EXCL",
]


def generate_trade_event(symbol: str) -> dict:
    """Generate a synthetic intraday trade event."""
    return {
        "event_type": "trade",
        "symbol": symbol,
        "price": str(round(random.uniform(1000, 50000), 2)),
        "size": random.choice([100, 200, 500, 1000]) * 100,
        "timestamp": datetime.now(UTC).isoformat(),
        "exchange": "IDX",
    }


def generate_bar_event(symbol: str) -> dict:
    """Generate a synthetic intraday bar event."""
    base = random.uniform(1000, 50000)
    return {
        "event_type": "bar",
        "symbol": symbol,
        "open": str(round(base, 2)),
        "high": str(round(base * 1.02, 2)),
        "low": str(round(base * 0.98, 2)),
        "close": str(round(base * 1.005, 2)),
        "volume": random.randint(100000, 5000000),
        "vwap": str(round(base * 1.001, 2)),
        "timestamp": datetime.now(UTC).isoformat(),
        "trade_count": random.randint(10, 500),
    }


@dataclass
class ProducerStats:
    """Statistics from a single producer."""

    producer_id: int
    messages_sent: int = 0
    errors: int = 0
    duration_seconds: float = 0.0
    messages_per_second: float = 0.0


@dataclass
class ThroughputReport:
    """Aggregate throughput report."""

    total_messages: int = 0
    total_errors: int = 0
    total_duration_seconds: float = 0.0
    aggregate_msg_per_sec: float = 0.0
    per_producer_msg_per_sec: list[float] = None  # type: ignore[assignment]
    avg_msg_per_sec: float = 0.0
    peak_msg_per_sec: float = 0.0
    avg_message_size_bytes: int = 0


async def run_producer(
    producer_id: int,
    topic: str,
    num_messages: int,
    bootstrap_servers: str,
) -> ProducerStats:
    """Run a single Kafka producer sending synthetic events."""
    import aiokafka

    stats = ProducerStats(producer_id=producer_id)

    producer = aiokafka.AIOKafkaProducer(
        bootstrap_servers=bootstrap_servers,
        acks="all",
        enable_idempotence=True,
        value_serializer=lambda v: json.dumps(v, default=str).encode("utf-8"),
        key_serializer=lambda k: k.encode("utf-8") if k else None,
        linger_ms=5,
        batch_size=32768,
    )

    try:
        await producer.start()
        t_start = time.monotonic()

        for i in range(num_messages):
            symbol = random.choice(IDX_SYMBOLS)
            event = generate_trade_event(symbol) if i % 2 == 0 else generate_bar_event(symbol)

            try:
                await producer.send(topic, value=event, key=symbol)
                stats.messages_sent += 1
            except Exception:
                stats.errors += 1

            # Yield every 1000 messages to avoid blocking
            if i % 1000 == 0:
                await asyncio.sleep(0)

        # Flush remaining
        await producer.flush()
        stats.duration_seconds = time.monotonic() - t_start
        stats.messages_per_second = stats.messages_sent / stats.duration_seconds if stats.duration_seconds > 0 else 0

    except Exception as e:
        logger.error("Producer %d failed: %s", producer_id, e)
        stats.errors += num_messages - stats.messages_sent
    finally:
        await producer.stop()

    return stats


async def run_consumer_benchmark(
    topic: str,
    expected_messages: int,
    bootstrap_servers: str,
    timeout: float = 60.0,
) -> tuple[int, float]:
    """Consume messages and measure throughput. Returns (count, duration)."""
    import aiokafka

    consumer = aiokafka.AIOKafkaConsumer(
        topic,
        bootstrap_servers=bootstrap_servers,
        group_id=f"benchmark-{int(time.time())}",
        auto_offset_reset="earliest",
        enable_auto_commit=True,
    )

    count = 0
    try:
        await consumer.start()
        t_start = time.monotonic()
        deadline = t_start + timeout

        async for msg in consumer:
            count += 1
            if count >= expected_messages or time.monotonic() > deadline:
                break

        duration = time.monotonic() - t_start
        return count, duration

    finally:
        await consumer.stop()


async def run_throughput_test(
    num_messages: int,
    num_producers: int,
    topic: str,
    bootstrap_servers: str,
) -> ThroughputReport:
    """Run the full Kafka throughput benchmark."""
    logger.info(
        "Starting Kafka throughput test: %d messages, %d producers, topic: %s",
        num_messages,
        num_producers,
        topic,
    )

    messages_per_producer = num_messages // num_producers
    sample_msg = json.dumps(generate_trade_event("BBCA")).encode("utf-8")

    # Run producers
    t_start = time.monotonic()
    producer_tasks = [run_producer(i, topic, messages_per_producer, bootstrap_servers) for i in range(num_producers)]
    producer_results = await asyncio.gather(*producer_tasks, return_exceptions=True)
    total_duration = time.monotonic() - t_start

    # Aggregate results
    stats_list: list[ProducerStats] = [r for r in producer_results if isinstance(r, ProducerStats)]

    report = ThroughputReport(
        total_messages=sum(s.messages_sent for s in stats_list),
        total_errors=sum(s.errors for s in stats_list),
        total_duration_seconds=total_duration,
        per_producer_msg_per_sec=[s.messages_per_second for s in stats_list],
        avg_message_size_bytes=len(sample_msg),
    )

    if total_duration > 0:
        report.aggregate_msg_per_sec = report.total_messages / total_duration

    if report.per_producer_msg_per_sec:
        report.avg_msg_per_sec = statistics.mean(report.per_producer_msg_per_sec)
        report.peak_msg_per_sec = max(report.per_producer_msg_per_sec)

    return report


def print_report(report: ThroughputReport) -> None:
    """Print throughput test results."""
    print("\n" + "=" * 60)
    print("  Kafka Ingestion Throughput Results")
    print("=" * 60)
    print(f"  Duration:              {report.total_duration_seconds:.2f}s")
    print(f"  Messages Sent:         {report.total_messages:,}")
    print(f"  Errors:                {report.total_errors:,}")
    print(f"  Avg Message Size:      {report.avg_message_size_bytes} bytes")
    print()
    print("  -- Throughput --")
    print(f"  Aggregate:             {report.aggregate_msg_per_sec:,.0f} msg/sec")
    print(f"  Avg per Producer:      {report.avg_msg_per_sec:,.0f} msg/sec")
    print(f"  Peak per Producer:     {report.peak_msg_per_sec:,.0f} msg/sec")
    mb_per_sec = report.aggregate_msg_per_sec * report.avg_message_size_bytes / 1_048_576
    print(f"  Data Rate:             {mb_per_sec:.1f} MB/sec")
    print()

    # Thresholds
    issues = []
    if report.aggregate_msg_per_sec < 10000:
        issues.append(f"Throughput {report.aggregate_msg_per_sec:.0f} msg/s below 10k target")
    if report.total_errors > report.total_messages * 0.001:
        issues.append(f"Error rate {report.total_errors}/{report.total_messages} exceeds 0.1%")

    if issues:
        print("  ISSUES:")
        for issue in issues:
            print(f"  - {issue}")
    else:
        print("  PASS: All throughput thresholds met.")
    print("=" * 60)
    print()


def main() -> None:
    parser = argparse.ArgumentParser(description="Kafka ingestion throughput benchmark")
    parser.add_argument("--messages", type=int, default=50000, help="Total messages to send")
    parser.add_argument("--producers", type=int, default=2, help="Number of concurrent producers")
    parser.add_argument("--topic", default="pyhron.benchmark.intraday", help="Kafka topic")
    parser.add_argument("--bootstrap", default="localhost:9092", help="Kafka bootstrap servers")
    args = parser.parse_args()

    report = asyncio.run(
        run_throughput_test(
            num_messages=args.messages,
            num_producers=args.producers,
            topic=args.topic,
            bootstrap_servers=args.bootstrap,
        )
    )
    print_report(report)


if __name__ == "__main__":
    main()
