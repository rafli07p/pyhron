"""Shared data types for the commodity linkage engine.

This module holds enums and dataclasses that are referenced by both the
top-level :mod:`~commodity_linkage_engine.commodity_to_stock_impact_engine`
orchestrator **and** the individual sensitivity models in
:mod:`~commodity_linkage_engine.commodity_sensitivity_models`.

Placing them here avoids circular imports: the engine imports the models,
and the models import these types -- neither side needs to import the other
at module-initialisation time.
"""

from __future__ import annotations

import enum
from dataclasses import dataclass, field


# Enums
class CommodityType(enum.Enum):
    """Supported commodity types."""

    CPO = "CPO"
    COAL = "COAL"
    NICKEL = "NICKEL"
    ICP_CRUDE = "ICP_CRUDE"


class ConfidenceLevel(enum.Enum):
    """Confidence tier for an impact estimate."""

    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


# Data Contracts
@dataclass(frozen=True)
class CommodityPriceChangeEvent:
    """Describes a commodity price movement.

    Attributes:
        commodity: Which commodity moved.
        change_pct: Percentage change (e.g. 10.0 = +10 %).
        change_absolute: Absolute change in commodity-native units
            (USD/ton for coal/nickel, MYR/ton for CPO, USD/bbl for ICP).
        source: Data source identifier (e.g. ``"reuters"``, ``"bisinfocus"``).
        timestamp_utc: ISO-8601 timestamp of the observation.
    """

    commodity: CommodityType
    change_pct: float
    change_absolute: float
    source: str
    timestamp_utc: str


@dataclass
class StockEarningsImpactEstimate:
    """Per-stock earnings impact estimate from a commodity price change.

    Attributes:
        ticker: IDX ticker (e.g. ``"AALI"``).
        commodity: The commodity driving the impact.
        revenue_impact_idr: Estimated revenue impact in IDR.
        net_income_impact_idr: Estimated net-income impact in IDR.
        eps_impact: Estimated EPS impact in IDR/share.
        impact_pct_of_revenue: Impact as a percentage of trailing revenue.
        confidence: Confidence tier.
        methodology: Human-readable description of the model.
        assumptions: Key assumptions underlying the estimate.
    """

    ticker: str
    commodity: CommodityType
    revenue_impact_idr: float
    net_income_impact_idr: float
    eps_impact: float
    impact_pct_of_revenue: float
    confidence: ConfidenceLevel
    methodology: str
    assumptions: list[str] = field(default_factory=list)
