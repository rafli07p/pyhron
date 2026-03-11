"""IDX-specific transaction cost model.

Encapsulates the unique cost structure of the Indonesia Stock Exchange:
  - Broker commission: 0.15% buy / 0.25% sell (Peraturan BEI standard retail)
  - IDX levy (BEI fee): 0.01% both sides
  - VAT on commission: 11% of commission (PPN)
  - Sales tax (PPh Final): 0.1% on sell side only
  - Market impact model: sqrt(participation_rate) × daily_spread
  - Lot size: 100 shares minimum
  - Settlement: T+2 (trade date + 2 business days)

Total roundtrip cost: ~0.5% to ~1.5% depending on liquidity.

Usage::

    model = IDXTransactionCostModel()
    cost = model.compute_trade_cost(price=5000, shares=1000, side="buy")
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import StrEnum

from shared.structured_json_logger import get_logger

logger = get_logger(__name__)


class TradeSide(StrEnum):
    """Trade side enumeration."""

    BUY = "buy"
    SELL = "sell"


@dataclass(frozen=True)
class TradeCostBreakdown:
    """Detailed breakdown of a single trade's costs.

    Attributes:
        gross_value: Trade value before costs (price × shares).
        commission: Brokerage commission in IDR.
        levy: IDX exchange levy in IDR.
        vat: VAT on commission in IDR.
        sales_tax: PPh Final tax in IDR (sell side only).
        market_impact: Estimated market impact cost in IDR.
        total_cost: Total transaction cost in IDR.
        net_value: Net trade value after costs.
        cost_bps: Total cost in basis points.
        settlement_date: Expected settlement date (T+2).
    """

    gross_value: float
    commission: float
    levy: float
    vat: float
    sales_tax: float
    market_impact: float
    total_cost: float
    net_value: float
    cost_bps: float
    settlement_date: datetime


class IDXTransactionCostModel:
    """Transaction cost model for IDX equities.

    IDX charges asymmetric fees:
      Buy:  0.15% commission + 0.01% levy + 11% VAT on commission
      Sell: 0.25% commission + 0.01% levy + 11% VAT on commission + 0.1% PPh

    Args:
        buy_commission_rate: Buy-side commission (default 0.0015 = 0.15%).
        sell_commission_rate: Sell-side commission (default 0.0025 = 0.25%).
        levy_rate: IDX exchange levy both sides (default 0.0001 = 0.01%).
        vat_on_commission_rate: VAT on commission (default 0.11 = 11%).
        sell_tax_rate: PPh Final tax on sell (default 0.001 = 0.1%).
        lot_size: IDX lot size (default 100 shares).
        settlement_days: Settlement cycle (default T+2).
    """

    def __init__(
        self,
        buy_commission_rate: float = 0.0015,
        sell_commission_rate: float = 0.0025,
        levy_rate: float = 0.0001,
        vat_on_commission_rate: float = 0.11,
        sell_tax_rate: float = 0.001,
        lot_size: int = 100,
        settlement_days: int = 2,
    ) -> None:
        self._buy_commission = buy_commission_rate
        self._sell_commission = sell_commission_rate
        self._levy_rate = levy_rate
        self._vat_rate = vat_on_commission_rate
        self._sell_tax = sell_tax_rate
        self._lot_size = lot_size
        self._settlement_days = settlement_days

        logger.info(
            "transaction_cost_model_initialised",
            buy_rate=self.buy_total_rate(),
            sell_rate=self.sell_total_rate(),
            lot_size=self._lot_size,
        )

    def buy_total_rate(self) -> float:
        """Total cost rate for buy transactions.

        commission + levy + VAT on commission.
        """
        commission = self._buy_commission
        levy = self._levy_rate
        vat = commission * self._vat_rate
        return commission + levy + vat

    def sell_total_rate(self) -> float:
        """Total cost rate for sell transactions.

        commission + levy + VAT on commission + PPh Final.
        """
        commission = self._sell_commission
        levy = self._levy_rate
        vat = commission * self._vat_rate
        return commission + levy + vat + self._sell_tax

    def effective_round_trip_cost(self) -> float:
        """Average one-way cost for vectorbt (half of round-trip)."""
        return (self.buy_total_rate() + self.sell_total_rate()) / 2.0

    def round_to_lot(self, shares: int) -> int:
        """Round share count down to nearest lot size."""
        return (shares // self._lot_size) * self._lot_size

    def estimate_market_impact(
        self,
        order_size_shares: int,
        avg_daily_volume: float,
        daily_spread_pct: float = 0.005,
    ) -> float:
        """Estimate market impact using square-root model.

        impact = sqrt(participation_rate) × daily_spread
        where participation_rate = order_size / avg_daily_volume

        Returns impact as a fraction (e.g. 0.002 = 0.2%).
        """
        if avg_daily_volume <= 0:
            return 0.0
        participation = order_size_shares / avg_daily_volume
        return math.sqrt(min(participation, 1.0)) * daily_spread_pct

    def compute_trade_cost(
        self,
        price: float,
        shares: int,
        side: TradeSide | str,
        trade_date: datetime | None = None,
        avg_daily_volume: float = 0.0,
        daily_spread_pct: float = 0.005,
    ) -> TradeCostBreakdown:
        """Compute full cost breakdown for a single trade.

        Args:
            price: Price per share in IDR.
            shares: Number of shares.
            side: ``"buy"`` or ``"sell"``.
            trade_date: Trade date for settlement calculation.
            avg_daily_volume: Average daily volume for market impact.
            daily_spread_pct: Daily spread percentage for impact model.

        Returns:
            TradeCostBreakdown with all cost components.
        """
        if isinstance(side, str):
            side = TradeSide(side)

        trade_date = trade_date or datetime.utcnow()
        gross_value = price * shares

        if side == TradeSide.BUY:
            commission = gross_value * self._buy_commission
        else:
            commission = gross_value * self._sell_commission

        levy = gross_value * self._levy_rate
        vat = commission * self._vat_rate
        sales_tax = gross_value * self._sell_tax if side == TradeSide.SELL else 0.0

        # Market impact
        impact_pct = self.estimate_market_impact(shares, avg_daily_volume, daily_spread_pct)
        market_impact = gross_value * impact_pct

        total_cost = commission + levy + vat + sales_tax + market_impact
        net_value = gross_value + total_cost if side == TradeSide.BUY else gross_value - total_cost
        cost_bps = (total_cost / gross_value * 10_000) if gross_value > 0 else 0.0

        settlement = self._compute_settlement_date(trade_date)

        return TradeCostBreakdown(
            gross_value=gross_value,
            commission=commission,
            levy=levy,
            vat=vat,
            sales_tax=sales_tax,
            market_impact=market_impact,
            total_cost=total_cost,
            net_value=net_value,
            cost_bps=cost_bps,
            settlement_date=settlement,
        )

    def _compute_settlement_date(self, trade_date: datetime) -> datetime:
        """Compute T+2 settlement date, skipping weekends."""
        settlement = trade_date
        business_days_added = 0
        while business_days_added < self._settlement_days:
            settlement += timedelta(days=1)
            if settlement.weekday() < 5:
                business_days_added += 1
        return settlement
