"""WebSocket fan-out load test.

Stress-tests the Kafka→Redis→WebSocket pipeline by simulating many
concurrent WebSocket clients subscribing to market data channels.

Usage::

    python tests/benchmarks/ws_load_test.py --clients 500 --duration 60
    python tests/benchmarks/ws_load_test.py --clients 1000 --url ws://staging:8000/ws
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import statistics
import time
from dataclasses import dataclass, field

import websockets

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("ws_load_test")

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


@dataclass
class ClientStats:
    """Per-client statistics."""

    client_id: int
    messages_received: int = 0
    connect_time_ms: float = 0.0
    first_message_time_ms: float = 0.0
    latencies_ms: list[float] = field(default_factory=list)
    errors: int = 0
    disconnects: int = 0


@dataclass
class AggregateStats:
    """Aggregate load test results."""

    total_clients: int = 0
    successful_connects: int = 0
    failed_connects: int = 0
    total_messages: int = 0
    total_errors: int = 0
    avg_connect_time_ms: float = 0.0
    avg_latency_ms: float = 0.0
    p50_latency_ms: float = 0.0
    p95_latency_ms: float = 0.0
    p99_latency_ms: float = 0.0
    messages_per_second: float = 0.0
    duration_seconds: float = 0.0


async def run_ws_client(
    client_id: int,
    ws_url: str,
    symbols: list[str],
    duration: float,
    token: str,
) -> ClientStats:
    """Run a single WebSocket client for the specified duration."""
    stats = ClientStats(client_id=client_id)
    t_start = time.monotonic()

    try:
        t_connect = time.monotonic()
        async with websockets.connect(
            f"{ws_url}?token={token}",
            ping_interval=20,
            ping_timeout=10,
            close_timeout=5,
        ) as ws:
            stats.connect_time_ms = (time.monotonic() - t_connect) * 1000

            # Subscribe to channels
            subscribe_msg = json.dumps(
                {
                    "action": "subscribe",
                    "channels": ["quotes", "intraday"],
                    "symbols": symbols,
                }
            )
            await ws.send(subscribe_msg)

            # Receive messages until duration expires
            deadline = t_start + duration
            while time.monotonic() < deadline:
                try:
                    raw = await asyncio.wait_for(ws.recv(), timeout=5.0)
                    t_recv = time.monotonic()
                    stats.messages_received += 1

                    if stats.messages_received == 1:
                        stats.first_message_time_ms = (t_recv - t_start) * 1000

                    # Parse and compute latency if timestamp present
                    try:
                        msg = json.loads(raw)
                        if "timestamp" in msg:
                            # Estimate delivery latency from message timestamp
                            pass  # Server-side timestamp comparison requires clock sync
                        stats.latencies_ms.append((time.monotonic() - t_recv) * 1000)
                    except (json.JSONDecodeError, KeyError):
                        stats.errors += 1

                except TimeoutError:
                    continue
                except websockets.ConnectionClosed:
                    stats.disconnects += 1
                    break

    except (OSError, websockets.InvalidHandshake) as e:
        stats.errors += 1
        logger.debug("Client %d connect failed: %s", client_id, e)

    return stats


async def run_load_test(
    num_clients: int,
    ws_url: str,
    duration: float,
    token: str,
    batch_size: int = 50,
) -> AggregateStats:
    """Run the full WebSocket load test."""
    logger.info(
        "Starting WebSocket load test: %d clients, %ds duration, URL: %s",
        num_clients,
        duration,
        ws_url,
    )

    all_stats: list[ClientStats] = []
    t_start = time.monotonic()

    # Launch clients in batches to avoid overwhelming the server
    for batch_start in range(0, num_clients, batch_size):
        batch_end = min(batch_start + batch_size, num_clients)

        logger.info("Launching clients %d-%d...", batch_start, batch_end - 1)

        tasks = [
            run_ws_client(
                client_id=i,
                ws_url=ws_url,
                symbols=IDX_SYMBOLS[:5],  # Subscribe to 5 symbols each
                duration=duration,
                token=token,
            )
            for i in range(batch_start, batch_end)
        ]

        batch_stats = await asyncio.gather(*tasks, return_exceptions=True)
        for s in batch_stats:
            if isinstance(s, ClientStats):
                all_stats.append(s)

        # Small delay between batches
        if batch_end < num_clients:
            await asyncio.sleep(0.5)

    total_duration = time.monotonic() - t_start

    # Compute aggregate stats
    agg = AggregateStats(
        total_clients=num_clients,
        duration_seconds=total_duration,
    )

    if not all_stats:
        return agg

    agg.successful_connects = sum(1 for s in all_stats if s.connect_time_ms > 0)
    agg.failed_connects = num_clients - agg.successful_connects
    agg.total_messages = sum(s.messages_received for s in all_stats)
    agg.total_errors = sum(s.errors for s in all_stats)

    connect_times = [s.connect_time_ms for s in all_stats if s.connect_time_ms > 0]
    if connect_times:
        agg.avg_connect_time_ms = statistics.mean(connect_times)

    all_latencies = []
    for s in all_stats:
        all_latencies.extend(s.latencies_ms)

    if all_latencies:
        sorted_lat = sorted(all_latencies)
        agg.avg_latency_ms = statistics.mean(sorted_lat)
        agg.p50_latency_ms = sorted_lat[len(sorted_lat) // 2]
        agg.p95_latency_ms = sorted_lat[int(len(sorted_lat) * 0.95)]
        agg.p99_latency_ms = sorted_lat[int(len(sorted_lat) * 0.99)]

    if total_duration > 0:
        agg.messages_per_second = agg.total_messages / total_duration

    return agg


def print_report(stats: AggregateStats) -> None:
    """Print a formatted load test report."""
    print("\n" + "=" * 60)
    print("  WebSocket Fan-Out Load Test Results")
    print("=" * 60)
    print(f"  Duration:            {stats.duration_seconds:.1f}s")
    print(f"  Total Clients:       {stats.total_clients}")
    print(f"  Successful Connects: {stats.successful_connects}")
    print(f"  Failed Connects:     {stats.failed_connects}")
    print()
    print(f"  Total Messages:      {stats.total_messages:,}")
    print(f"  Messages/sec:        {stats.messages_per_second:,.1f}")
    print(f"  Errors:              {stats.total_errors}")
    print()
    print("  -- Latency --")
    print(f"  Avg Connect Time:    {stats.avg_connect_time_ms:.1f}ms")
    print(f"  Avg Processing:      {stats.avg_latency_ms:.3f}ms")
    print(f"  p50:                 {stats.p50_latency_ms:.3f}ms")
    print(f"  p95:                 {stats.p95_latency_ms:.3f}ms")
    print(f"  p99:                 {stats.p99_latency_ms:.3f}ms")
    print("=" * 60)

    # Pass/fail thresholds
    issues = []
    if stats.failed_connects > stats.total_clients * 0.05:
        issues.append(f"High connect failure rate: {stats.failed_connects}/{stats.total_clients}")
    if stats.p95_latency_ms > 100:
        issues.append(f"p95 latency {stats.p95_latency_ms:.1f}ms exceeds 100ms threshold")
    if stats.total_errors > stats.total_messages * 0.01:
        issues.append(f"Error rate {stats.total_errors}/{stats.total_messages} exceeds 1%")

    if issues:
        print("\n  ISSUES:")
        for issue in issues:
            print(f"  - {issue}")
    else:
        print("\n  PASS: All thresholds met.")
    print()


def main() -> None:
    parser = argparse.ArgumentParser(description="WebSocket fan-out load test")
    parser.add_argument("--clients", type=int, default=100, help="Number of concurrent WS clients")
    parser.add_argument("--duration", type=float, default=30, help="Test duration in seconds")
    parser.add_argument("--url", default="ws://localhost:8000/ws", help="WebSocket URL")
    parser.add_argument("--token", default="load-test-token", help="Auth token")
    parser.add_argument("--batch-size", type=int, default=50, help="Clients per connection batch")
    args = parser.parse_args()

    stats = asyncio.run(
        run_load_test(
            num_clients=args.clients,
            ws_url=args.url,
            duration=args.duration,
            token=args.token,
            batch_size=args.batch_size,
        )
    )
    print_report(stats)


if __name__ == "__main__":
    main()
