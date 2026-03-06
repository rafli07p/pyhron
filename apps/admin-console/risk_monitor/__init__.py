"""Real-time risk monitoring dashboard backend."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from typing import Any

import structlog

logger = structlog.get_logger(__name__)


@dataclass
class RiskAlert:
    alert_id: str
    level: str  # INFO, WARNING, CRITICAL
    message: str
    metric: str
    current_value: float
    threshold: float
    tenant_id: str
    timestamp: datetime = field(default_factory=datetime.utcnow)


@dataclass
class RiskSummary:
    portfolio_var: Decimal
    gross_exposure: Decimal
    net_exposure: Decimal
    max_drawdown: Decimal
    daily_pnl: Decimal
    open_positions: int
    active_alerts: int
    tenant_id: str
    as_of: datetime = field(default_factory=datetime.utcnow)


class RiskMonitor:
    """Aggregate risk metrics and alerts for the admin console."""

    def __init__(self) -> None:
        self._alerts: list[RiskAlert] = []
        self._limits: dict[str, dict[str, float]] = {}

    async def get_risk_summary(self, tenant_id: str) -> RiskSummary:
        """Compute current risk summary from portfolio and risk services."""
        active = [a for a in self._alerts if a.tenant_id == tenant_id]
        return RiskSummary(
            portfolio_var=Decimal("0"),
            gross_exposure=Decimal("0"),
            net_exposure=Decimal("0"),
            max_drawdown=Decimal("0"),
            daily_pnl=Decimal("0"),
            open_positions=0,
            active_alerts=len(active),
            tenant_id=tenant_id,
        )

    async def get_alerts(
        self, tenant_id: str, level: str | None = None
    ) -> list[RiskAlert]:
        alerts = [a for a in self._alerts if a.tenant_id == tenant_id]
        if level:
            alerts = [a for a in alerts if a.level == level]
        return alerts

    async def set_risk_limits(
        self, tenant_id: str, limits: dict[str, float]
    ) -> None:
        self._limits[tenant_id] = limits
        logger.info("risk_limits_updated", tenant_id=tenant_id, limits=limits)

    async def get_exposure_report(self, tenant_id: str) -> dict[str, Any]:
        return {
            "tenant_id": tenant_id,
            "sector_exposure": {},
            "currency_exposure": {},
            "country_exposure": {},
            "generated_at": datetime.utcnow().isoformat(),
        }

    def _emit_alert(self, alert: RiskAlert) -> None:
        self._alerts.append(alert)
        logger.warning(
            "risk_alert",
            level=alert.level,
            metric=alert.metric,
            value=alert.current_value,
            threshold=alert.threshold,
            tenant_id=alert.tenant_id,
        )
