"""System health monitoring for the admin console."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

import structlog

logger = structlog.get_logger(__name__)


@dataclass
class ComponentHealth:
    name: str
    status: str  # healthy, degraded, down
    latency_ms: float | None = None
    last_check: datetime = field(default_factory=datetime.utcnow)
    details: dict[str, Any] = field(default_factory=dict)


@dataclass
class SystemMetrics:
    cpu_usage_pct: float
    memory_usage_pct: float
    disk_usage_pct: float
    active_connections: int
    orders_per_second: float
    api_latency_p99_ms: float
    uptime_seconds: float
    timestamp: datetime = field(default_factory=datetime.utcnow)


class SystemHealth:
    """Monitor the health and performance of all system components."""

    COMPONENTS = ["api", "postgres", "redis", "kafka", "market_data", "execution"]

    def __init__(self, redis_url: str | None = None, db_url: str | None = None) -> None:
        self._redis_url = redis_url
        self._db_url = db_url
        self._start_time = datetime.utcnow()

    async def get_health_status(self) -> list[ComponentHealth]:
        checks = [self._check_component(name) for name in self.COMPONENTS]
        return await asyncio.gather(*checks)

    async def get_metrics(self) -> SystemMetrics:
        uptime = (datetime.utcnow() - self._start_time).total_seconds()
        return SystemMetrics(
            cpu_usage_pct=0.0,
            memory_usage_pct=0.0,
            disk_usage_pct=0.0,
            active_connections=0,
            orders_per_second=0.0,
            api_latency_p99_ms=0.0,
            uptime_seconds=uptime,
        )

    async def check_connectivity(self) -> dict[str, bool]:
        results: dict[str, bool] = {}
        if self._redis_url:
            try:
                import redis.asyncio as aioredis

                r = aioredis.from_url(self._redis_url)
                await r.ping()
                results["redis"] = True
                await r.aclose()
            except Exception:
                results["redis"] = False

        if self._db_url:
            try:
                from sqlalchemy.ext.asyncio import create_async_engine

                engine = create_async_engine(self._db_url)
                async with engine.connect() as conn:
                    await conn.execute("SELECT 1")
                results["postgres"] = True
                await engine.dispose()
            except Exception:
                results["postgres"] = False

        return results

    async def get_uptime(self) -> float:
        return (datetime.utcnow() - self._start_time).total_seconds()

    async def _check_component(self, name: str) -> ComponentHealth:
        return ComponentHealth(name=name, status="healthy")
