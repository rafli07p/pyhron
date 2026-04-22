"""Quick integration test for IDX XBRL scraper.

Run: poetry run python scripts/test_xbrl_scraper.py [SYMBOL] [YEAR] [PERIOD]
Default: BBCA 2023 TW1

Requires running Postgres (DATABASE_URL) for the upsert path.
"""
from __future__ import annotations

import asyncio
import sys

sys.path.insert(0, ".")

from data_platform.equity_ingestion.idx_xbrl_scraper import IDXXBRLScraper


async def main() -> None:
    symbol = sys.argv[1] if len(sys.argv) > 1 else "BBCA"
    year = int(sys.argv[2]) if len(sys.argv) > 2 else 2023
    period = sys.argv[3] if len(sys.argv) > 3 else "TW1"

    scraper = IDXXBRLScraper()
    print(f"Testing IDX XBRL scraper with {symbol} {period} {year}...")
    results = await scraper.scrape_symbol(symbol, year, period)
    for r in results:
        print(f"  {r.symbol}/{r.period}/{r.year}:")
        print(
            f"    inserted={r.rows_inserted}, "
            f"updated={r.rows_updated}, "
            f"skipped={r.rows_skipped}, "
            f"duration_ms={r.duration_ms:.0f}",
        )
        if r.errors:
            print(f"    errors={r.errors}")


if __name__ == "__main__":
    asyncio.run(main())
