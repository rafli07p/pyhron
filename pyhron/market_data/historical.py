from __future__ import annotations

from datetime import date

from pyhron.market_data.client import OHLCVBar


class HistoricalDataLoader:
    def __init__(self, cache_dir: str, source: str = "yfinance") -> None:
        self.cache_dir = cache_dir
        self.source = source

    def load(
        self, symbols: list[str], start_date: date, end_date: date
    ) -> dict[str, list[OHLCVBar]]:
        raise NotImplementedError
