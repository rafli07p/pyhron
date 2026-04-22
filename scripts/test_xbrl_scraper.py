"""Quick integration test for IDX XBRL scraper.

Run: poetry run python scripts/test_xbrl_scraper.py

Requires running Postgres (DATABASE_URL) for the upsert path.
"""
from __future__ import annotations

import asyncio
import sys

sys.path.insert(0, ".")

from data_platform.equity_ingestion.idx_xbrl_scraper import IDXXBRLScraper


async def main() -> None:
    scraper = IDXXBRLScraper()
    print("Testing IDX XBRL scraper with BBCA TW1 2023...")
    results = await scraper.scrape_symbol("BBCA", 2023, "TW1")
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
