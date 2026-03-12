"""Async wrapper around yfinance for IDX data.

yfinance is synchronous; wrap all calls in asyncio.to_thread().
IDX symbol format for yfinance: "BBCA.JK"
"""

from __future__ import annotations

import asyncio
from datetime import date, timedelta
from decimal import Decimal, InvalidOperation

import yfinance as yf

from data_platform.adapters.eodhd_adapter import EODHDOHLCVRecord
from shared.structured_json_logger import get_logger

logger = get_logger(__name__)


class YFinanceAdapter:
    """Async wrapper around yfinance for IDX data."""

    IDX_SUFFIX = ".JK"

    async def get_eod_data(
        self,
        symbol: str,
        date_from: date,
        date_to: date,
    ) -> list[EODHDOHLCVRecord]:
        """Returns records in the same schema as EODHDAdapter for interchangeability."""
        yf_symbol = f"{symbol}{self.IDX_SUFFIX}" if not symbol.endswith(self.IDX_SUFFIX) else symbol
        bare_symbol = symbol.replace(self.IDX_SUFFIX, "")

        def _fetch() -> list[EODHDOHLCVRecord]:
            ticker = yf.Ticker(yf_symbol)
            df = ticker.history(
                start=date_from.isoformat(),
                end=(date_to + timedelta(days=1)).isoformat(),
                auto_adjust=False,
            )
            if df is None or df.empty:
                return []

            records: list[EODHDOHLCVRecord] = []
            for idx, row in df.iterrows():
                try:
                    row_date = idx.date() if hasattr(idx, "date") else date.fromisoformat(str(idx)[:10])
                    adj_close = row.get("Adj Close", row["Close"])
                    records.append(
                        EODHDOHLCVRecord(
                            symbol=bare_symbol,
                            date=row_date,
                            open=Decimal(str(round(float(row["Open"]), 2))),
                            high=Decimal(str(round(float(row["High"]), 2))),
                            low=Decimal(str(round(float(row["Low"]), 2))),
                            close=Decimal(str(round(float(row["Close"]), 2))),
                            adjusted_close=Decimal(str(round(float(adj_close), 2))),
                            volume=int(row.get("Volume", 0)),
                            source="yfinance",
                        )
                    )
                except (KeyError, InvalidOperation, ValueError) as e:
                    logger.warning("skipping_yfinance_row", symbol=yf_symbol, error=str(e))
            return records

        return await asyncio.to_thread(_fetch)

    async def get_info(self, symbol: str) -> dict:
        """Fetch instrument metadata (sector, industry, market cap)."""
        yf_symbol = f"{symbol}{self.IDX_SUFFIX}" if not symbol.endswith(self.IDX_SUFFIX) else symbol

        def _fetch() -> dict:
            ticker = yf.Ticker(yf_symbol)
            return dict(ticker.info) if ticker.info else {}

        return await asyncio.to_thread(_fetch)
