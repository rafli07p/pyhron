from __future__ import annotations

from decimal import Decimal
from enum import Enum

from pydantic import BaseModel, Field


class RiskViolationType(str, Enum):
    ORDER_SIZE_EXCEEDED = "order_size_exceeded"
    POSITION_LIMIT_EXCEEDED = "position_limit_exceeded"
    VAR_LIMIT_EXCEEDED = "var_limit_exceeded"
    DRAWDOWN_EXCEEDED = "drawdown_exceeded"
    CONCENTRATION_EXCEEDED = "concentration_exceeded"
    LEVERAGE_EXCEEDED = "leverage_exceeded"


class RiskViolation(BaseModel):
    violation_type: RiskViolationType
    message: str
    current_value: Decimal
    limit_value: Decimal


class RiskCheckResult(BaseModel):
    passed: bool
    violations: list[RiskViolation] = Field(default_factory=list)
    warnings: list[str] | None = None
