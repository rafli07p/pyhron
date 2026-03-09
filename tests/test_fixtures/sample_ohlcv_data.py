"""Sample OHLCV data for testing.

Provides 5 trading days of realistic IDX equity data for BBCA, TLKM, and ASII.
Prices are in IDR. Volume is in shares.
"""

from __future__ import annotations

from datetime import UTC, datetime

BBCA_OHLCV = [
    {
        "time": datetime(2025, 1, 6, 9, 0, tzinfo=UTC),
        "symbol": "BBCA",
        "exchange": "IDX",
        "open": 9200,
        "high": 9350,
        "low": 9150,
        "close": 9300,
        "volume": 12_500_000,
    },
    {
        "time": datetime(2025, 1, 7, 9, 0, tzinfo=UTC),
        "symbol": "BBCA",
        "exchange": "IDX",
        "open": 9300,
        "high": 9400,
        "low": 9250,
        "close": 9375,
        "volume": 10_800_000,
    },
    {
        "time": datetime(2025, 1, 8, 9, 0, tzinfo=UTC),
        "symbol": "BBCA",
        "exchange": "IDX",
        "open": 9375,
        "high": 9500,
        "low": 9350,
        "close": 9475,
        "volume": 14_200_000,
    },
    {
        "time": datetime(2025, 1, 9, 9, 0, tzinfo=UTC),
        "symbol": "BBCA",
        "exchange": "IDX",
        "open": 9475,
        "high": 9525,
        "low": 9400,
        "close": 9425,
        "volume": 9_600_000,
    },
    {
        "time": datetime(2025, 1, 10, 9, 0, tzinfo=UTC),
        "symbol": "BBCA",
        "exchange": "IDX",
        "open": 9425,
        "high": 9500,
        "low": 9375,
        "close": 9450,
        "volume": 11_300_000,
    },
]

TLKM_OHLCV = [
    {
        "time": datetime(2025, 1, 6, 9, 0, tzinfo=UTC),
        "symbol": "TLKM",
        "exchange": "IDX",
        "open": 3800,
        "high": 3850,
        "low": 3750,
        "close": 3825,
        "volume": 45_000_000,
    },
    {
        "time": datetime(2025, 1, 7, 9, 0, tzinfo=UTC),
        "symbol": "TLKM",
        "exchange": "IDX",
        "open": 3825,
        "high": 3900,
        "low": 3800,
        "close": 3875,
        "volume": 38_500_000,
    },
    {
        "time": datetime(2025, 1, 8, 9, 0, tzinfo=UTC),
        "symbol": "TLKM",
        "exchange": "IDX",
        "open": 3875,
        "high": 3925,
        "low": 3850,
        "close": 3900,
        "volume": 42_100_000,
    },
    {
        "time": datetime(2025, 1, 9, 9, 0, tzinfo=UTC),
        "symbol": "TLKM",
        "exchange": "IDX",
        "open": 3900,
        "high": 3950,
        "low": 3875,
        "close": 3880,
        "volume": 36_800_000,
    },
    {
        "time": datetime(2025, 1, 10, 9, 0, tzinfo=UTC),
        "symbol": "TLKM",
        "exchange": "IDX",
        "open": 3880,
        "high": 3920,
        "low": 3860,
        "close": 3910,
        "volume": 40_200_000,
    },
]

ASII_OHLCV = [
    {
        "time": datetime(2025, 1, 6, 9, 0, tzinfo=UTC),
        "symbol": "ASII",
        "exchange": "IDX",
        "open": 5200,
        "high": 5300,
        "low": 5150,
        "close": 5275,
        "volume": 22_000_000,
    },
    {
        "time": datetime(2025, 1, 7, 9, 0, tzinfo=UTC),
        "symbol": "ASII",
        "exchange": "IDX",
        "open": 5275,
        "high": 5350,
        "low": 5225,
        "close": 5325,
        "volume": 18_500_000,
    },
    {
        "time": datetime(2025, 1, 8, 9, 0, tzinfo=UTC),
        "symbol": "ASII",
        "exchange": "IDX",
        "open": 5325,
        "high": 5400,
        "low": 5300,
        "close": 5375,
        "volume": 20_100_000,
    },
    {
        "time": datetime(2025, 1, 9, 9, 0, tzinfo=UTC),
        "symbol": "ASII",
        "exchange": "IDX",
        "open": 5375,
        "high": 5425,
        "low": 5325,
        "close": 5350,
        "volume": 17_600_000,
    },
    {
        "time": datetime(2025, 1, 10, 9, 0, tzinfo=UTC),
        "symbol": "ASII",
        "exchange": "IDX",
        "open": 5350,
        "high": 5400,
        "low": 5300,
        "close": 5380,
        "volume": 19_300_000,
    },
]

ALL_OHLCV = BBCA_OHLCV + TLKM_OHLCV + ASII_OHLCV


def make_invalid_ohlcv_high_below_low():
    """Return a row where high < low (invalid)."""
    return {
        "time": datetime(2025, 1, 6, 9, 0, tzinfo=UTC),
        "symbol": "BBCA",
        "exchange": "IDX",
        "open": 9200,
        "high": 9100,
        "low": 9150,
        "close": 9300,
        "volume": 10_000,
    }


def make_invalid_ohlcv_negative_volume():
    """Return a row with negative volume (invalid)."""
    return {
        "time": datetime(2025, 1, 6, 9, 0, tzinfo=UTC),
        "symbol": "BBCA",
        "exchange": "IDX",
        "open": 9200,
        "high": 9350,
        "low": 9150,
        "close": 9300,
        "volume": -500,
    }


def make_invalid_ohlcv_zero_price():
    """Return a row with zero open price (invalid)."""
    return {
        "time": datetime(2025, 1, 6, 9, 0, tzinfo=UTC),
        "symbol": "BBCA",
        "exchange": "IDX",
        "open": 0,
        "high": 9350,
        "low": 9150,
        "close": 9300,
        "volume": 10_000,
    }
