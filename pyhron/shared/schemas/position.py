from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel


class PositionSnapshot(BaseModel):
    symbol: str
    quantity: Decimal
    average_entry_price: Decimal
    current_price: Decimal
    unrealized_pnl: Decimal
    realized_pnl: Decimal
    market_value: Decimal
    strategy_id: str
    updated_at: datetime
