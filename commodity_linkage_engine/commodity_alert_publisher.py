"""Publish commodity impact alerts to Kafka.

When a commodity price change exceeds configurable thresholds, this
publisher generates impact alerts and sends them to the
``pyhron.commodity.stock-impact-alerts`` Kafka topic for downstream
consumption by the risk engine and notification services.

Usage::

    async with CommodityAlertPublisher(kafka_servers="kafka:29092") as pub:
        await pub.publish_impact_alerts(event, estimates)
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

from shared.kafka_producer_consumer import PyhronProducer, Topics
from shared.structured_json_logger import get_logger
from commodity_linkage_engine.commodity_to_stock_impact_engine import (
    CommodityPriceChangeEvent,
    StockEarningsImpactEstimate,
)

logger = get_logger(__name__)

# ── Alert severity thresholds ───────────────────────────────────────────────

_SEVERITY_THRESHOLDS: dict[str, float] = {
    "CRITICAL": 5.0,   # > 5% revenue impact
    "HIGH": 2.0,       # > 2% revenue impact
    "MEDIUM": 1.0,     # > 1% revenue impact
    "LOW": 0.0,        # Any impact
}


class CommodityAlertPublisher:
    """Publish commodity-driven stock impact alerts to Kafka.

    Generates severity-classified alerts when commodity price movements
    create material earnings impact for covered IDX equities.

    Args:
        kafka_servers: Kafka bootstrap servers.
        topic: Target Kafka topic for alerts.
        min_severity: Minimum severity level to publish (default ``LOW``).
    """

    def __init__(
        self,
        kafka_servers: str = "kafka:29092",
        topic: str = Topics.COMMODITY_STOCK_IMPACT_ALERTS,
        min_severity: str = "LOW",
    ) -> None:
        self._kafka_servers = kafka_servers
        self._topic = topic
        self._min_severity = min_severity
        self._producer: PyhronProducer | None = None

        logger.info(
            "commodity_alert_publisher_initialised",
            topic=topic,
            min_severity=min_severity,
        )

    async def start(self) -> None:
        """Start the underlying Kafka producer."""
        self._producer = PyhronProducer(self._kafka_servers)
        await self._producer.start()

    async def stop(self) -> None:
        """Stop the Kafka producer."""
        if self._producer is not None:
            await self._producer.stop()
            self._producer = None

    async def __aenter__(self) -> CommodityAlertPublisher:
        await self.start()
        return self

    async def __aexit__(self, *exc: object) -> None:
        await self.stop()

    async def publish_impact_alerts(
        self,
        event: CommodityPriceChangeEvent,
        estimates: list[StockEarningsImpactEstimate],
    ) -> int:
        """Publish impact alerts for each affected stock.

        Args:
            event: The commodity price change event that triggered alerts.
            estimates: List of per-stock earnings impact estimates.

        Returns:
            Number of alerts published.
        """
        if self._producer is None:
            raise RuntimeError("Publisher not started — call start() or use async with")

        published = 0
        severity_order = list(_SEVERITY_THRESHOLDS.keys())
        min_idx = severity_order.index(self._min_severity)

        for estimate in estimates:
            severity = self._classify_severity(estimate.impact_pct_of_revenue)
            sev_idx = severity_order.index(severity)
            if sev_idx > min_idx:
                continue

            alert = self._build_alert_payload(event, estimate, severity)
            try:
                await self._producer._producer.send_and_wait(
                    self._topic,
                    value=json.dumps(alert).encode("utf-8"),
                    key=estimate.ticker.encode("utf-8"),
                )
                published += 1
                logger.info(
                    "commodity_alert_published",
                    ticker=estimate.ticker,
                    severity=severity,
                    commodity=event.commodity.value,
                )
            except Exception as exc:
                logger.error(
                    "commodity_alert_publish_failed",
                    ticker=estimate.ticker,
                    error=str(exc),
                )

        logger.info(
            "commodity_alert_batch_complete",
            total_estimates=len(estimates),
            published=published,
        )
        return published

    @staticmethod
    def _classify_severity(impact_pct: float) -> str:
        """Classify alert severity based on revenue impact percentage.

        Args:
            impact_pct: Impact as percentage of trailing revenue.

        Returns:
            Severity string: CRITICAL, HIGH, MEDIUM, or LOW.
        """
        abs_impact = abs(impact_pct)
        for severity, threshold in _SEVERITY_THRESHOLDS.items():
            if abs_impact >= threshold:
                return severity
        return "LOW"

    @staticmethod
    def _build_alert_payload(
        event: CommodityPriceChangeEvent,
        estimate: StockEarningsImpactEstimate,
        severity: str,
    ) -> dict[str, Any]:
        """Build JSON-serialisable alert payload.

        Args:
            event: Commodity price change event.
            estimate: Stock earnings impact estimate.
            severity: Alert severity classification.

        Returns:
            Dictionary payload for Kafka message.
        """
        return {
            "alert_type": "commodity_stock_impact",
            "severity": severity,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "commodity": event.commodity.value,
            "commodity_change_pct": event.change_pct,
            "ticker": estimate.ticker,
            "revenue_impact_idr": estimate.revenue_impact_idr,
            "eps_impact": estimate.eps_impact,
            "impact_pct_of_revenue": estimate.impact_pct_of_revenue,
            "confidence": estimate.confidence.value,
            "methodology": estimate.methodology,
        }
