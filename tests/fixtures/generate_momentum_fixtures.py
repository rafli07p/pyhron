"""Generate synthetic OHLCV data for momentum strategy testing.

Creates data for 50 IDX-like symbols over 1200 trading days with known
statistical properties:
  - Momentum factor present (AR(1) = 0.02 monthly autocorrelation)
  - Realistic IDR price levels (IDR 500 - IDR 50,000)
  - Realistic volume (avg daily value IDR 5B - IDR 100B)
  - 5 synthetic sectors, each with 10 symbols
  - Fixed random seed (42) for reproducibility

Usage::

    python -m tests.fixtures.generate_momentum_fixtures
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path

import numpy as np
import pandas as pd

SEED = 42
N_SYMBOLS = 50
N_DAYS = 1200
SECTORS = ["FINANCE", "CONSUMER", "ENERGY", "BASIC_MATERIALS", "INFRASTRUCTURE"]
SYMBOLS_PER_SECTOR = 10

# Price range by sector (IDR)
SECTOR_PRICE_RANGES = {
    "FINANCE": (2000, 15000),
    "CONSUMER": (1000, 10000),
    "ENERGY": (500, 8000),
    "BASIC_MATERIALS": (500, 5000),
    "INFRASTRUCTURE": (1000, 12000),
}

SECTOR_VOLUME_RANGES = {
    "FINANCE": (5_000_000, 50_000_000),
    "CONSUMER": (2_000_000, 30_000_000),
    "ENERGY": (3_000_000, 40_000_000),
    "BASIC_MATERIALS": (1_000_000, 20_000_000),
    "INFRASTRUCTURE": (2_000_000, 25_000_000),
}


def generate_symbols() -> list[dict]:
    """Generate 50 synthetic IDX symbols across 5 sectors."""
    symbols = []
    for sector_idx, sector in enumerate(SECTORS):
        for i in range(SYMBOLS_PER_SECTOR):
            sym_num = sector_idx * SYMBOLS_PER_SECTOR + i
            symbol = f"SYM{sym_num:03d}"
            symbols.append(
                {
                    "symbol": symbol,
                    "sector": sector,
                    "lot_size": 100,
                    "is_active": True,
                }
            )
    return symbols


def generate_trading_dates(n_days: int, start: datetime) -> list[datetime]:
    """Generate n trading days (skip weekends)."""
    dates = []
    current = start
    while len(dates) < n_days:
        if current.weekday() < 5:
            dates.append(current)
        current += timedelta(days=1)
    return dates


def generate_price_series(
    rng: np.random.Generator,
    n_days: int,
    initial_price: float,
    monthly_autocorrelation: float = 0.02,
    daily_vol: float = 0.02,
) -> np.ndarray:
    """Generate a price series with momentum (positive autocorrelation).

    Uses AR(1) process on monthly returns to inject momentum factor.
    """
    prices = np.zeros(n_days)
    prices[0] = initial_price

    # Generate daily returns with autocorrelation
    prev_monthly_return = 0.0
    for day in range(1, n_days):
        # Monthly momentum component (reset roughly every 21 days)
        if day % 21 == 0:
            prev_monthly_return = monthly_autocorrelation * prev_monthly_return + rng.normal(0, 0.05)
        daily_drift = prev_monthly_return / 21
        noise = rng.normal(0, daily_vol)
        daily_return = daily_drift + noise
        prices[day] = prices[day - 1] * (1 + daily_return)
        prices[day] = max(prices[day], 50)  # floor at IDR 50

    return prices


def generate_fixtures() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Generate all fixture data.

    Returns
    -------
    tuple of (prices, volumes, trading_values, instrument_metadata)
    """
    rng = np.random.default_rng(SEED)
    symbols_meta = generate_symbols()
    start_date = datetime(2019, 1, 2, tzinfo=UTC)
    dates = generate_trading_dates(N_DAYS, start_date)
    date_index = pd.DatetimeIndex(dates)

    price_data = {}
    volume_data = {}
    value_data = {}

    for meta in symbols_meta:
        symbol = meta["symbol"]
        sector = meta["sector"]
        price_range = SECTOR_PRICE_RANGES[sector]
        vol_range = SECTOR_VOLUME_RANGES[sector]

        initial_price = rng.uniform(price_range[0], price_range[1])
        prices = generate_price_series(
            rng,
            N_DAYS,
            initial_price,
            monthly_autocorrelation=0.02,
            daily_vol=0.015 + rng.uniform(0, 0.015),
        )
        price_data[symbol] = prices

        avg_vol = rng.uniform(vol_range[0], vol_range[1])
        volumes = (avg_vol * (1 + rng.normal(0, 0.3, N_DAYS))).clip(min=10000).astype(int)
        volume_data[symbol] = volumes

        value_data[symbol] = prices * volumes

    prices_df = pd.DataFrame(price_data, index=date_index)
    volumes_df = pd.DataFrame(volume_data, index=date_index)
    values_df = pd.DataFrame(value_data, index=date_index)
    metadata_df = pd.DataFrame(symbols_meta)

    return prices_df, volumes_df, values_df, metadata_df


def save_fixtures(output_dir: Path | None = None) -> None:
    """Generate and save fixture files."""
    if output_dir is None:
        output_dir = Path(__file__).parent

    prices, volumes, values, metadata = generate_fixtures()

    prices.to_parquet(output_dir / "momentum_prices.parquet")
    volumes.to_parquet(output_dir / "momentum_volumes.parquet")
    values.to_parquet(output_dir / "momentum_trading_values.parquet")
    metadata.to_csv(output_dir / "momentum_instrument_metadata.csv", index=False)

    import sys

    sys.stdout.write(f"Fixtures saved to {output_dir}\n")
    sys.stdout.write(f"  Prices: {prices.shape}\n")
    sys.stdout.write(f"  Volumes: {volumes.shape}\n")
    sys.stdout.write(f"  Trading values: {values.shape}\n")
    sys.stdout.write(f"  Metadata: {metadata.shape}\n")


if __name__ == "__main__":
    save_fixtures()
