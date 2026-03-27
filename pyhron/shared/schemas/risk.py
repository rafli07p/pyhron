from __future__ import annotations

from decimal import Decimal

from pydantic import BaseModel, Field


class RiskLimits(BaseModel):
    max_position_size: Decimal = Field(gt=0)
    max_order_size: Decimal = Field(gt=0)
    max_daily_loss: Decimal = Field(gt=0)
    max_drawdown_pct: Decimal = Field(gt=0, le=1)
    max_var: Decimal = Field(gt=0)
    max_concentration_pct: Decimal = Field(gt=0, le=1)
    max_leverage: Decimal = Field(gt=0)
