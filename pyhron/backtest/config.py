from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal


@dataclass
class BacktestConfig:
    start_date: date
    end_date: date
    symbols: list[str]
    initial_capital: Decimal
    commission_rate: Decimal
    slippage_bps: int
    data_frequency: str
    benchmark_symbol: str
