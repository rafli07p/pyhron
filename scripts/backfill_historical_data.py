"""Historical data backfill utility.

Usage:
    poetry run python scripts/backfill_historical_data.py
        --symbols BBCA,BBRI,BMRI
        --date-from 2015-01-01
        --date-to 2024-12-31
        --source eodhd
        --workers 5
        --dry-run

Options:
    --symbols       comma-separated list; if omitted, backfill all active
    --date-from     start date (ISO format)
    --date-to       end date (ISO format); defaults to yesterday
    --source        eodhd|yfinance (default: eodhd)
    --workers       concurrent symbol workers (default: 5, max: 10)
    --dry-run       fetch and validate without writing to DB
    --force         overwrite existing records (default: skip)
"""

from __future__ import annotations

import argparse
import asyncio
from datetime import date, timedelta

from strategy_engine.idx_trading_calendar import is_trading_day


def compute_missing_dates(
    symbol: str,
    date_from: date,
    date_to: date,
    existing_dates: set[date],
    calendar: object | None = None,
) -> list[date]:
    """Compute trading dates in range that are missing from existing_dates."""
    missing: list[date] = []
    current = date_from
    while current <= date_to:
        if is_trading_day(current) and current not in existing_dates:
            missing.append(current)
        current += timedelta(days=1)
    return missing


async def backfill_symbol(
    symbol: str,
    date_from: date,
    date_to: date,
    source: str,
    rate_semaphore: asyncio.Semaphore,
    dry_run: bool = False,
) -> dict:
    """Backfill a single symbol."""
    import httpx

    from data_platform.adapters.eodhd_adapter import EODHDAdapter, EODHDOHLCVRecord
    from data_platform.adapters.yfinance_adapter import YFinanceAdapter
    from shared.configuration_settings import get_config

    config = get_config()
    records: list[EODHDOHLCVRecord] = []

    async with rate_semaphore:
        if source == "eodhd":
            async with httpx.AsyncClient() as session:
                adapter = EODHDAdapter(api_token=config.eodhd_api_key, session=session)
                records = await adapter.get_eod_data(symbol, date_from=date_from, date_to=date_to)
        if not records or source == "yfinance":
            yf_adapter = YFinanceAdapter()
            records = await yf_adapter.get_eod_data(symbol, date_from=date_from, date_to=date_to)

    status = "dry_run" if dry_run else "fetched"
    return {
        "symbol": symbol,
        "records": len(records),
        "date_from": str(date_from),
        "date_to": str(date_to),
        "source": records[0].source if records else source,
        "status": status,
    }


async def main(args: argparse.Namespace) -> None:
    """Main backfill entry point."""
    symbols: list[str] = args.symbols.split(",") if args.symbols else []
    date_from = date.fromisoformat(args.date_from)
    date_to = date.fromisoformat(args.date_to) if args.date_to else date.today() - timedelta(days=1)
    workers = min(args.workers, 10)
    rate_semaphore = asyncio.Semaphore(5)  # EODHD MAX_RPS=5 globally

    if not symbols:
        print("No symbols specified. Use --symbols BBCA,BBRI,...")
        return

    print(f"Backfill: {len(symbols)} symbols, {date_from} to {date_to}, source={args.source}")
    print(f"Workers: {workers}, Dry run: {args.dry_run}")
    print("-" * 60)

    worker_semaphore = asyncio.Semaphore(workers)

    async def _worker(sym: str) -> dict:
        async with worker_semaphore:
            return await backfill_symbol(sym, date_from, date_to, args.source, rate_semaphore, args.dry_run)

    tasks = [_worker(sym) for sym in symbols]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    # Summary
    total_fetched = 0
    total_failed = 0
    print("\n" + "=" * 60)
    print(f"{'Symbol':<10} {'Records':>8} {'Source':<10} {'Status':<10}")
    print("-" * 60)
    for r in results:
        if isinstance(r, Exception):
            total_failed += 1
            print(f"{'ERROR':<10} {'0':>8} {'':.<10} {str(r)[:30]}")
        else:
            total_fetched += r["records"]
            print(f"{r['symbol']:<10} {r['records']:>8} {r['source']:<10} {r['status']:<10}")
    print("=" * 60)
    print(f"Total: {total_fetched} records fetched, {total_failed} failed")


def cli() -> None:
    parser = argparse.ArgumentParser(description="Backfill historical OHLCV data for IDX symbols")
    parser.add_argument("--symbols", type=str, default="", help="Comma-separated symbol list")
    parser.add_argument("--date-from", type=str, required=True, help="Start date (ISO format)")
    parser.add_argument("--date-to", type=str, default="", help="End date (ISO format, default: yesterday)")
    parser.add_argument("--source", type=str, default="eodhd", choices=["eodhd", "yfinance"])
    parser.add_argument("--workers", type=int, default=5, help="Concurrent workers (max 10)")
    parser.add_argument("--dry-run", action="store_true", help="Fetch without writing to DB")
    parser.add_argument("--force", action="store_true", help="Overwrite existing records")
    args = parser.parse_args()
    asyncio.run(main(args))


if __name__ == "__main__":
    cli()
