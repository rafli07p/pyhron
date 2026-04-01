"""IDX realistic transaction cost model for backtesting.

Provides accurate cost estimation for the Indonesia Stock Exchange,
including asymmetric brokerage, exchange levy, VAT, and market impact.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal
from typing import TYPE_CHECKING, Literal

if TYPE_CHECKING:
    import pandas as pd


@dataclass
class IDXTransactionCostModel:
    """IDX realistic cost structure as of 2024.

    Attributes
    ----------
    brokerage_buy_bps:
        Buy-side brokerage fee in basis points (default 15).
    brokerage_sell_bps:
        Sell-side brokerage fee in basis points (default 25, includes OJK tax).
    market_impact_bps_per_pct_adv:
        Market impact in bps per 1% of ADV traded (default 10).
    min_commission_idr:
        Minimum commission per trade in IDR.
    """

    brokerage_buy_bps: float = 15.0
    brokerage_sell_bps: float = 25.0
    market_impact_bps_per_pct_adv: float = 10.0
    min_commission_idr: Decimal = Decimal("5000")

    def cost(
        self,
        notional: Decimal,
        side: Literal["buy", "sell"],
        pct_of_adv: float,
    ) -> Decimal:
        """Compute total transaction cost in IDR.

        Parameters
        ----------
        notional:
            Trade value in IDR.
        side:
            Trade direction.
        pct_of_adv:
            Trade size as fraction of ADV (e.g. 0.01 = 1%).

        Returns
        -------
        Decimal
            Total cost in IDR.
        """
        if side == "buy":
            brokerage_bps = Decimal(str(self.brokerage_buy_bps))
        else:
            brokerage_bps = Decimal(str(self.brokerage_sell_bps))

        brokerage = (notional * brokerage_bps / Decimal("10000")).quantize(Decimal("1"), rounding=ROUND_HALF_UP)
        brokerage = max(brokerage, self.min_commission_idr)

        # Market impact
        impact_bps = Decimal(str(self.market_impact_bps_per_pct_adv * pct_of_adv * 100))
        impact = (notional * impact_bps / Decimal("10000")).quantize(Decimal("1"), rounding=ROUND_HALF_UP)

        return brokerage + impact

    def apply_to_returns(
        self,
        returns: pd.Series,
        turnover: pd.Series,
        adv_fraction: float = 0.01,
    ) -> pd.Series:
        """Subtract realistic transaction costs from a return series.

        Parameters
        ----------
        returns:
            Daily return series.
        turnover:
            Daily fractional turnover (0 to 1).
        adv_fraction:
            Assumed trade size as fraction of ADV.

        Returns
        -------
        pd.Series
            Net returns after costs.
        """
        # Average cost per unit of turnover
        avg_bps = (self.brokerage_buy_bps + self.brokerage_sell_bps) / 2
        impact_bps = self.market_impact_bps_per_pct_adv * adv_fraction * 100
        total_cost_bps = avg_bps + impact_bps

        # Convert bps to fraction
        cost_fraction = total_cost_bps / 10_000

        # Subtract cost proportional to turnover
        costs = turnover * cost_fraction
        return returns - costs
