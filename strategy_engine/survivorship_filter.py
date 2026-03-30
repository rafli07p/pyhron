"""Survivorship bias prevention filter for backtesting.

Validates that symbols were actually listed and active on the as-of date,
preventing forward-looking bias from including stocks not yet listed or
already delisted.

Audit item M-1: No survivorship bias prevention in strategies.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from shared.structured_json_logger import get_logger

if TYPE_CHECKING:
    from datetime import date, datetime

    import pandas as pd

logger = get_logger(__name__)


def filter_tradable_symbols(
    symbols: list[str],
    as_of_date: date | datetime,
    instrument_metadata: pd.DataFrame | None,
) -> list[str]:
    """Filter symbols to only those tradable on the given date.

    Checks listing_date, delisting_date, and is_active fields from
    instrument metadata to prevent survivorship bias in backtesting.

    Args:
        symbols: Candidate symbols to filter.
        as_of_date: Date to check tradability against.
        instrument_metadata: DataFrame with columns ``symbol``,
            ``listing_date``, ``delisting_date``, ``is_active``.
            If ``None``, returns symbols unchanged (no filtering).

    Returns:
        Filtered list of tradable symbols.
    """
    if instrument_metadata is None or instrument_metadata.empty:
        return symbols

    # Normalise date
    check_date = as_of_date.date() if hasattr(as_of_date, "date") else as_of_date

    if "symbol" in instrument_metadata.columns:
        meta_lookup = instrument_metadata.set_index("symbol")
    else:
        meta_lookup = instrument_metadata

    tradable: list[str] = []
    excluded = 0

    for symbol in symbols:
        if symbol not in meta_lookup.index:
            # No metadata — assume tradable (conservative)
            tradable.append(symbol)
            continue

        row = meta_lookup.loc[symbol]

        # Check is_active
        if not row.get("is_active", True):
            excluded += 1
            continue

        # Survivorship: skip if not yet listed
        listing = row.get("listing_date")
        if listing is not None and check_date < listing:
            excluded += 1
            continue

        # Survivorship: skip if already delisted
        delisting = row.get("delisting_date")
        if delisting is not None and check_date > delisting:
            excluded += 1
            continue

        tradable.append(symbol)

    if excluded > 0:
        logger.info(
            "survivorship_filter_applied",
            original=len(symbols),
            tradable=len(tradable),
            excluded=excluded,
            as_of_date=str(check_date),
        )

    return tradable
