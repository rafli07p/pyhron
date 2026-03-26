from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal
from enum import Enum
from uuid import UUID


class TradeDirection(str, Enum):
    BUY = "buy"
    SELL = "sell"


@dataclass
class FillRecord:
    fill_id: UUID
    order_id: UUID
    symbol: str
    direction: TradeDirection
    quantity: Decimal
    price: Decimal
    commission: Decimal
    timestamp: datetime
    strategy_id: str


@dataclass
class RealizedPnLResult:
    gross_pnl: Decimal
    total_commissions: Decimal
    net_pnl: Decimal


@dataclass
class PnLReport:
    report_date: date
    total_realized_pnl: Decimal
    total_unrealized_pnl: Decimal
    by_symbol: dict[str, dict[str, Decimal]] = field(default_factory=dict)


@dataclass
class PnLSummary:
    total_trades: int
    win_rate: float
    total_net_pnl: Decimal
    total_gross_pnl: Decimal
    total_commissions: Decimal
