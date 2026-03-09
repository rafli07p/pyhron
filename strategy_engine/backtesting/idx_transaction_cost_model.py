"""IDX-specific transaction cost model.

Encapsulates the unique cost structure of the Indonesia Stock Exchange:
  - Brokerage commission: 0.15% on buy, 0.15% on sell.
  - Sales tax (PPh Final): 0.1% on sell side only.
  - Total: 0.15% buy, 0.25% sell (0.15% commission + 0.1% tax).
  - Lot size: 100 shares minimum.
  - Settlement: T+2 (trade date + 2 business days).

Usage::

    model = IDXTransactionCostModel()
    cost = model.compute_trade_cost(price=5000, shares=1000, side="buy")
"""

from __future__ import annotations

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
        gross_value: Trade value before costs (price * shares).
        commission: Brokerage commission in IDR.
        sales_tax: PPh Final tax in IDR (sell side only).
        total_cost: Total transaction cost in IDR.
        net_value: Net trade value after costs.
        cost_bps: Total cost in basis points.
        settlement_date: Expected settlement date (T+2).
    """

    gross_value: float
    commission: float
    sales_tax: float
    total_cost: float
    net_value: float
    cost_bps: float
    settlement_date: datetime


class IDXTransactionCostModel:
    """Transaction cost model for IDX equities.

    IDX charges asymmetric fees: 0.15% on buy and 0.25% on sell
    (0.15% commission + 0.1% PPh Final sales tax).

    Args:
        buy_commission_rate: Buy-side commission (default 0.0015 = 0.15%).
        sell_commission_rate: Sell-side commission (default 0.0015 = 0.15%).
        sell_tax_rate: PPh Final tax on sell (default 0.001 = 0.1%).
        lot_size: IDX lot size (default 100 shares).
        settlement_days: Settlement cycle (default T+2).
    """

    def __init__(
        self,
        buy_commission_rate: float = 0.0015,
        sell_commission_rate: float = 0.0015,
        sell_tax_rate: float = 0.001,
        lot_size: int = 100,
        settlement_days: int = 2,
    ) -> None:
        self._buy_commission = buy_commission_rate
        self._sell_commission = sell_commission_rate
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
        """Total cost rate for buy transactions (commission only)."""
        return self._buy_commission

    def sell_total_rate(self) -> float:
        """Total cost rate for sell transactions (commission + tax)."""
        return self._sell_commission + self._sell_tax

    def effective_round_trip_cost(self) -> float:
        """Average one-way cost for vectorbt (half of round-trip)."""
        return (self.buy_total_rate() + self.sell_total_rate()) / 2.0

    def round_to_lot(self, shares: int) -> int:
        """Round share count down to nearest lot size.

        Args:
            shares: Desired number of shares.

        Returns:
            Shares rounded down to nearest lot (multiple of 100).
        """
        return (shares // self._lot_size) * self._lot_size

    def compute_trade_cost(
        self,
        price: float,
        shares: int,
        side: TradeSide | str,
        trade_date: datetime | None = None,
    ) -> TradeCostBreakdown:
        """Compute full cost breakdown for a single trade.

        Args:
            price: Price per share in IDR.
            shares: Number of shares (must be a multiple of lot_size).
            side: ``"buy"`` or ``"sell"``.
            trade_date: Trade date for settlement calculation.

        Returns:
            TradeCostBreakdown with all cost components.
        """
        if isinstance(side, str):
            side = TradeSide(side)

        trade_date = trade_date or datetime.utcnow()
        gross_value = price * shares

        if side == TradeSide.BUY:
            commission = gross_value * self._buy_commission
            sales_tax = 0.0
        else:
            commission = gross_value * self._sell_commission
            sales_tax = gross_value * self._sell_tax

        total_cost = commission + sales_tax
        net_value = gross_value + total_cost if side == TradeSide.BUY else gross_value - total_cost
        cost_bps = (total_cost / gross_value * 10_000) if gross_value > 0 else 0.0

        settlement = self._compute_settlement_date(trade_date)

        return TradeCostBreakdown(
            gross_value=gross_value,
            commission=commission,
            sales_tax=sales_tax,
            total_cost=total_cost,
            net_value=net_value,
            cost_bps=cost_bps,
            settlement_date=settlement,
        )

    def _compute_settlement_date(self, trade_date: datetime) -> datetime:
        """Compute T+2 settlement date, skipping weekends.

        Args:
            trade_date: Original trade date.

        Returns:
            Settlement date (T+2 business days).
        """
        settlement = trade_date
        business_days_added = 0
        while business_days_added < self._settlement_days:
            settlement += timedelta(days=1)
            if settlement.weekday() < 5:  # Monday–Friday
                business_days_added += 1
        return settlement
