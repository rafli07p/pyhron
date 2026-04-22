"""Parse-only test for IDX XBRL scraper.

Downloads an instance.zip from IDX, extracts the XBRL, parses it,
and prints all extracted metrics. No database required.

Run: poetry run python scripts/test_xbrl_parse_only.py [SYMBOL] [YEAR] [PERIOD]
Default: BBCA 2023 TW1
"""
from __future__ import annotations

import asyncio
import io
import sys
import zipfile

from curl_cffi.requests import AsyncSession as CurlSession

sys.path.insert(0, ".")

from data_platform.equity_ingestion.idx_xbrl_scraper import (
    IDX_BASE_URL,
    IDX_HEADERS,
    IDXFilingDiscoverer,
    IDXXBRLParser,
)


async def main() -> None:
    symbol = sys.argv[1] if len(sys.argv) > 1 else "BBCA"
    year = int(sys.argv[2]) if len(sys.argv) > 2 else 2023
    period = sys.argv[3] if len(sys.argv) > 3 else "TW1"

    print(f"[1/4] Discovering filings for {symbol}/{year}/{period}...")
    async with CurlSession(impersonate="chrome120", timeout=60) as client:
        discoverer = IDXFilingDiscoverer(client)
        filings = await discoverer.discover(symbol, year, period)

        if not filings:
            print(f"  No filings found for {symbol}/{year}/{period}")
            return

        print(f"  Found {len(filings)} filing(s)")
        filing = filings[0]
        print(f"  file_path={filing.file_path}")

        print("[2/4] Downloading instance.zip...")
        encoded = filing.file_path.replace(" ", "%20")
        url = f"{IDX_BASE_URL}{encoded}"
        resp = await client.get(
            url,
            headers={
                "User-Agent": IDX_HEADERS["User-Agent"],
                "Referer": IDX_BASE_URL + "/",
            },
            allow_redirects=True,
            timeout=60,
        )
        if resp.status_code >= 400:
            print(f"  Download failed: HTTP {resp.status_code}")
            return
        print(f"  Downloaded {len(resp.content):,} bytes")

        print("[3/4] Extracting XBRL...")
        with zipfile.ZipFile(io.BytesIO(resp.content)) as zf:
            xbrl_files = [n for n in zf.namelist() if n.endswith(".xbrl")]
            if not xbrl_files:
                print("  No .xbrl in zip")
                return
            xbrl_bytes = zf.read(xbrl_files[0])
            xbrl = xbrl_bytes.decode("utf-8", errors="ignore")
            print(f"  Extracted {len(xbrl):,} chars from {xbrl_files[0]}")

        print("[4/4] Parsing XBRL...")
        parser = IDXXBRLParser()
        statements = parser.parse(
            xbrl_content=xbrl,
            symbol=symbol,
            fiscal_year=year,
            period=period,
            source_url=url,
        )
        print(f"  Parsed {len(statements)} statement(s)\n")

        for stmt in statements:
            print(
                f"  -- {stmt.statement_type.upper()} "
                f"[{stmt.fiscal_year} Q{stmt.quarter or 'Y'}] "
                f"period_end={stmt.period_end}",
            )
            for metric, value in sorted(stmt.metrics.items()):
                print(f"     {metric:<28} {value:>20,}")
            print()


if __name__ == "__main__":
    asyncio.run(main())
