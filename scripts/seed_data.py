#!/usr/bin/env python3
"""
Seed historical market data for development and testing.

Downloads OHLCV data from yfinance for IDX (Indonesian Stock Exchange)
blue chips and other configured symbols, then stores it in the database
and local cache for offline development.

Usage:
    python scripts/seed_data.py                          # Default IDX blue chips, 2 years
    python scripts/seed_data.py --symbols BBCA.JK TLKM.JK
    python scripts/seed_data.py --period 5y              # 5 years of data
    python scripts/seed_data.py --output-dir data/cache  # Custom output directory
    python scripts/seed_data.py --db-only                # Insert to DB only (no files)
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import sys
from datetime import UTC, datetime
from pathlib import Path

import pandas as pd
import yfinance as yf
from dotenv import load_dotenv

load_dotenv()

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("pyhron.seed_data")

# =============================================================================
# Configuration
# =============================================================================
DEFAULT_SYMBOLS = {
    "idx_bluechips": [
        "BBCA.JK",
        "BBRI.JK",
        "BMRI.JK",
        "TLKM.JK",
        "ASII.JK",
        "UNVR.JK",
        "HMSP.JK",
        "GGRM.JK",
        "ICBP.JK",
        "KLBF.JK",
        "BBNI.JK",
        "INDF.JK",
        "PGAS.JK",
        "SMGR.JK",
        "JSMR.JK",
    ],
    "idx_index": ["^JKSE"],
    "us_reference": ["SPY", "QQQ", "AAPL", "MSFT", "GOOGL", "AMZN", "META", "TSLA", "NVDA", "JPM"],
    "us_index": ["^GSPC", "^DJI"],
    "commodities": ["GC=F", "CL=F"],
    "fx": ["USDIDR=X", "EURUSD=X"],
}

DATABASE_URL = os.environ.get("DATABASE_URL", "")
if not DATABASE_URL:
    raise ValueError(
        "DATABASE_URL environment variable is required. Example: postgresql+asyncpg://user:pass@localhost:5432/dbname"
    )
SYNC_DATABASE_URL = DATABASE_URL.replace("+asyncpg", "")
DEFAULT_TENANT = "dev"


# =============================================================================
# Data Download
# =============================================================================
def download_symbol_data(
    symbol: str,
    period: str = "2y",
    interval: str = "1d",
) -> pd.DataFrame | None:
    """Download historical data for a single symbol using yfinance."""
    try:
        logger.info(f"Downloading {symbol} ({period}, {interval})...")
        ticker = yf.Ticker(symbol)
        df = ticker.history(period=period, interval=interval)

        if df.empty:
            logger.warning(f"No data returned for {symbol}")
            return None

        df = df.rename(
            columns={
                "Open": "open",
                "High": "high",
                "Low": "low",
                "Close": "close",
                "Volume": "volume",
                "Dividends": "dividends",
                "Stock Splits": "splits",
            }
        )

        df["symbol"] = symbol
        df.index.name = "date"

        if df.index.tz is not None:
            df.index = df.index.tz_convert("UTC").tz_localize(None)

        logger.info(
            f"  {symbol}: {len(df)} bars, "
            f"{df.index.min().strftime('%Y-%m-%d')} to {df.index.max().strftime('%Y-%m-%d')}"
        )
        return df

    except Exception as e:
        logger.error(f"Failed to download {symbol}: {e}")
        return None


def download_all_symbols(
    symbols: list[str],
    period: str = "2y",
    interval: str = "1d",
) -> dict[str, pd.DataFrame]:
    """Download data for multiple symbols."""
    results = {}
    total = len(symbols)

    for i, symbol in enumerate(symbols, 1):
        logger.info(f"[{i}/{total}] Processing {symbol}...")
        df = download_symbol_data(symbol, period=period, interval=interval)
        if df is not None:
            results[symbol] = df

    logger.info(f"Downloaded data for {len(results)}/{total} symbols.")
    return results


# =============================================================================
# Data Storage
# =============================================================================
def save_to_parquet(
    data: dict[str, pd.DataFrame],
    output_dir: Path,
) -> None:
    """Save downloaded data to Parquet files for fast local access."""
    output_dir.mkdir(parents=True, exist_ok=True)

    for symbol, df in data.items():
        safe_name = symbol.replace(".", "_").replace("=", "_").replace("^", "idx_")
        filepath = output_dir / f"{safe_name}.parquet"
        df.to_parquet(filepath, engine="pyarrow", compression="snappy")
        logger.info(f"  Saved {filepath} ({len(df)} rows)")

    combined = pd.concat(data.values(), ignore_index=False)
    combined_path = output_dir / "all_symbols.parquet"
    combined.to_parquet(combined_path, engine="pyarrow", compression="snappy")
    logger.info(f"  Saved combined dataset: {combined_path} ({len(combined)} rows)")

    metadata = {
        "symbols": list(data.keys()),
        "total_rows": len(combined),
        "date_range": {
            "start": str(combined.index.min()),
            "end": str(combined.index.max()),
        },
        "downloaded_at": datetime.now(UTC).isoformat(),
    }
    metadata_path = output_dir / "metadata.json"
    with open(metadata_path, "w") as f:
        json.dump(metadata, f, indent=2)
    logger.info(f"  Saved metadata: {metadata_path}")


def save_to_csv(
    data: dict[str, pd.DataFrame],
    output_dir: Path,
) -> None:
    """Save downloaded data to CSV files."""
    csv_dir = output_dir / "csv"
    csv_dir.mkdir(parents=True, exist_ok=True)

    for symbol, df in data.items():
        safe_name = symbol.replace(".", "_").replace("=", "_").replace("^", "idx_")
        filepath = csv_dir / f"{safe_name}.csv"
        df.to_csv(filepath)
        logger.info(f"  Saved {filepath}")


def insert_to_database_sync(
    data: dict[str, pd.DataFrame],
    database_url: str,
) -> None:
    """Insert downloaded data into PostgreSQL using synchronous SQLAlchemy."""
    from sqlalchemy import create_engine

    engine = create_engine(database_url)
    total_inserted = 0

    for symbol, df in data.items():
        logger.info(f"  Inserting {symbol} ({len(df)} rows)...")
        try:
            records = pd.DataFrame(
                {
                    "symbol": symbol,
                    "timestamp": df.index,
                    "open": df["open"],
                    "high": df["high"],
                    "low": df["low"],
                    "close": df["close"],
                    "volume": df["volume"].astype(int),
                    "source": "yfinance",
                    "tenant_id": DEFAULT_TENANT,
                }
            )

            records.to_sql(
                "ohlcv_records",
                engine,
                if_exists="append",
                index=False,
                method="multi",
            )
            total_inserted += len(records)
            logger.info(f"  Stored {len(records)} bars for {symbol}")

        except Exception as e:
            logger.error(f"  Error inserting {symbol}: {e}")

    logger.info(f"Inserted {total_inserted} total rows into database.")


# =============================================================================
# Data Validation
# =============================================================================
def validate_data(data: dict[str, pd.DataFrame]) -> dict[str, list[str]]:
    """Validate downloaded data quality."""
    issues: dict[str, list[str]] = {}

    for symbol, df in data.items():
        symbol_issues = []

        nan_counts = df[["open", "high", "low", "close"]].isna().sum()
        for col, count in nan_counts.items():
            if count > 0:
                symbol_issues.append(f"{count} NaN values in {col}")

        invalid_ohlc = (
            (df["high"] < df["low"]).sum() + (df["high"] < df["open"]).sum() + (df["high"] < df["close"]).sum()
        )
        if invalid_ohlc > 0:
            symbol_issues.append(f"{invalid_ohlc} invalid OHLC relationships")

        zero_prices = (df["close"] <= 0).sum()
        if zero_prices > 0:
            symbol_issues.append(f"{zero_prices} zero/negative close prices")

        if len(df) > 1:
            date_diffs = pd.Series(df.index).diff().dt.days
            large_gaps = (date_diffs > 7).sum()
            if large_gaps > 0:
                symbol_issues.append(f"{large_gaps} gaps > 7 calendar days")

        duplicates = df.index.duplicated().sum()
        if duplicates > 0:
            symbol_issues.append(f"{duplicates} duplicate dates")

        if symbol_issues:
            issues[symbol] = symbol_issues
        else:
            logger.info(f"  [OK] {symbol}: {len(df)} bars, data quality checks passed")

    if issues:
        logger.warning("Data quality issues found:")
        for symbol, symbol_issues in issues.items():
            for issue in symbol_issues:
                logger.warning(f"  [{symbol}] {issue}")

    return issues


# =============================================================================
# Main
# =============================================================================
def get_symbol_list(args: argparse.Namespace) -> list[str]:
    """Resolve the list of symbols to download."""
    if args.symbols:
        return args.symbols

    symbols = []
    categories = args.categories.split(",") if args.categories else DEFAULT_SYMBOLS.keys()
    for category in categories:
        category = category.strip()
        if category in DEFAULT_SYMBOLS:
            symbols.extend(DEFAULT_SYMBOLS[category])
        else:
            logger.warning(f"Unknown category: {category}")

    return list(set(symbols))


def main() -> None:
    """Entry point for the seed data script."""
    parser = argparse.ArgumentParser(description="Seed historical market data for Pyhron development")
    parser.add_argument(
        "--symbols",
        nargs="+",
        help="Specific symbols to download (e.g., BBCA.JK TLKM.JK)",
    )
    parser.add_argument(
        "--categories",
        type=str,
        default=None,
        help="Comma-separated categories: idx_bluechips,idx_index,us_reference,commodities,fx",
    )
    parser.add_argument(
        "--period",
        type=str,
        default="2y",
        help="Data period (e.g., 1y, 2y, 5y, max). Default: 2y",
    )
    parser.add_argument(
        "--interval",
        type=str,
        default="1d",
        help="Data interval (e.g., 1d, 1h, 5m). Default: 1d",
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default=str(PROJECT_ROOT / "data" / "historical"),
        help="Output directory for data files",
    )
    parser.add_argument("--db-only", action="store_true", help="Insert to database only")
    parser.add_argument("--no-db", action="store_true", help="Skip database insertion")
    parser.add_argument("--csv", action="store_true", help="Also save as CSV files")
    parser.add_argument(
        "--validate",
        action="store_true",
        default=True,
        help="Validate data quality (default: True)",
    )
    args = parser.parse_args()

    symbols = get_symbol_list(args)
    logger.info(f"Symbols to download: {symbols}")
    logger.info(f"Period: {args.period}, Interval: {args.interval}")

    data = download_all_symbols(symbols, period=args.period, interval=args.interval)

    if not data:
        logger.error("No data downloaded. Exiting.")
        sys.exit(1)

    if args.validate:
        logger.info("Validating data quality...")
        validate_data(data)

    if not args.db_only:
        output_dir = Path(args.output_dir)
        logger.info(f"Saving data to {output_dir}...")
        save_to_parquet(data, output_dir)
        if args.csv:
            save_to_csv(data, output_dir)

    if not args.no_db:
        logger.info("Inserting data into database...")
        try:
            insert_to_database_sync(data, SYNC_DATABASE_URL)
        except Exception as e:
            logger.warning(f"Database insertion skipped: {e}")

    total_rows = sum(len(df) for df in data.values())
    logger.info("=" * 60)
    logger.info("SEED DATA SUMMARY")
    logger.info(f"  Symbols: {len(data)}")
    logger.info(f"  Total rows: {total_rows:,}")
    logger.info(f"  Period: {args.period}")
    if not args.db_only:
        logger.info(f"  Output: {args.output_dir}")
    logger.info("=" * 60)


if __name__ == "__main__":
    main()
