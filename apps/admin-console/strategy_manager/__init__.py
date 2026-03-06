"""Strategy lifecycle management for the admin console."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum
from typing import Any
from uuid import UUID, uuid4

import structlog

logger = structlog.get_logger(__name__)


class StrategyStatus(StrEnum):
    DRAFT = "DRAFT"
    DEPLOYED = "DEPLOYED"
    RUNNING = "RUNNING"
    PAUSED = "PAUSED"
    STOPPED = "STOPPED"
    ERROR = "ERROR"


@dataclass
class StrategyRecord:
    strategy_id: UUID
    name: str
    version: str
    status: StrategyStatus
    tenant_id: str
    config: dict[str, Any] = field(default_factory=dict)
    deployed_at: datetime | None = None
    created_at: datetime = field(default_factory=datetime.utcnow)


class StrategyManager:
    """Manage strategy deployment, monitoring, and lifecycle."""

    def __init__(self) -> None:
        self._strategies: dict[UUID, StrategyRecord] = {}
        self._lock = asyncio.Lock()

    async def deploy_strategy(
        self,
        name: str,
        config: dict[str, Any],
        tenant_id: str,
        version: str = "1.0.0",
    ) -> StrategyRecord:
        async with self._lock:
            record = StrategyRecord(
                strategy_id=uuid4(),
                name=name,
                version=version,
                status=StrategyStatus.DEPLOYED,
                tenant_id=tenant_id,
                config=config,
                deployed_at=datetime.utcnow(),
            )
            self._strategies[record.strategy_id] = record
            logger.info(
                "strategy_deployed",
                strategy_id=str(record.strategy_id),
                name=name,
                tenant_id=tenant_id,
            )
            return record

    async def pause_strategy(self, strategy_id: UUID, tenant_id: str) -> StrategyRecord:
        async with self._lock:
            record = self._get(strategy_id, tenant_id)
            record.status = StrategyStatus.PAUSED
            logger.info("strategy_paused", strategy_id=str(strategy_id))
            return record

    async def resume_strategy(self, strategy_id: UUID, tenant_id: str) -> StrategyRecord:
        async with self._lock:
            record = self._get(strategy_id, tenant_id)
            record.status = StrategyStatus.RUNNING
            logger.info("strategy_resumed", strategy_id=str(strategy_id))
            return record

    async def stop_strategy(self, strategy_id: UUID, tenant_id: str) -> StrategyRecord:
        async with self._lock:
            record = self._get(strategy_id, tenant_id)
            record.status = StrategyStatus.STOPPED
            logger.info("strategy_stopped", strategy_id=str(strategy_id))
            return record

    async def get_strategy_status(self, strategy_id: UUID, tenant_id: str) -> StrategyRecord:
        return self._get(strategy_id, tenant_id)

    async def list_strategies(self, tenant_id: str) -> list[StrategyRecord]:
        return [s for s in self._strategies.values() if s.tenant_id == tenant_id]

    def _get(self, strategy_id: UUID, tenant_id: str) -> StrategyRecord:
        record = self._strategies.get(strategy_id)
        if record is None or record.tenant_id != tenant_id:
            raise KeyError(f"Strategy {strategy_id} not found for tenant {tenant_id}")
        return record
