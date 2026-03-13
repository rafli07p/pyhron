"""Indonesian Stock Exchange transaction cost model.

Provides accurate round-trip cost calculations including broker commission,
IDX levy, VAT on commission, and PPh final income tax on sell transactions.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal


@dataclass(frozen=True)
class TransactionCost:
    """Breakdown of IDX transaction costs."""

    transaction_value_idr: Decimal
    commission_idr: Decimal
    idx_levy_idr: Decimal
    vat_idr: Decimal
    pph_idr: Decimal
    total_cost_idr: Decimal
    effective_cost_pct: Decimal


class IDXTransactionCostModel:
    """Indonesian Stock Exchange transaction cost model.

    Buy side:
        Broker commission: 0.15% of transaction value (minimum IDR 10,000)
        IDX levy: 0.01% of transaction value
        VAT on commission: 11% of broker commission
        Total buy cost: ~0.167% of transaction value

    Sell side:
        Broker commission: 0.25% of transaction value (minimum IDR 10,000)
        IDX levy: 0.01% of transaction value
        VAT on commission: 11% of broker commission
        Income tax (PPh): 0.10% of transaction value (final tax)
        Total sell cost: ~0.388% of transaction value

    Round-trip cost: ~0.555% of transaction value.
    """

    BUY_COMMISSION_PCT = Decimal("0.0015")
    SELL_COMMISSION_PCT = Decimal("0.0025")
    IDX_LEVY_PCT = Decimal("0.0001")
    VAT_ON_COMMISSION = Decimal("0.11")
    PPH_SELL_PCT = Decimal("0.0010")
    MIN_COMMISSION_IDR = Decimal("10000")

    def compute_buy_cost(self, transaction_value_idr: Decimal) -> TransactionCost:
        """Compute buy-side transaction costs.

        Args:
            transaction_value_idr: price * quantity_shares
        """
        commission = max(
            (transaction_value_idr * self.BUY_COMMISSION_PCT).quantize(Decimal("1"), ROUND_HALF_UP),
            self.MIN_COMMISSION_IDR,
        )
        idx_levy = (transaction_value_idr * self.IDX_LEVY_PCT).quantize(Decimal("1"), ROUND_HALF_UP)
        vat = (commission * self.VAT_ON_COMMISSION).quantize(Decimal("1"), ROUND_HALF_UP)
        pph = Decimal("0")
        total = commission + idx_levy + vat + pph
        effective_pct = (
            (total / transaction_value_idr * 100).quantize(Decimal("0.0001"), ROUND_HALF_UP)
            if transaction_value_idr > 0
            else Decimal("0")
        )

        return TransactionCost(
            transaction_value_idr=transaction_value_idr,
            commission_idr=commission,
            idx_levy_idr=idx_levy,
            vat_idr=vat,
            pph_idr=pph,
            total_cost_idr=total,
            effective_cost_pct=effective_pct,
        )

    def compute_sell_cost(self, transaction_value_idr: Decimal) -> TransactionCost:
        """Compute sell-side transaction costs including PPh final tax.

        PPh 0.10% is a final income tax on all sell transactions,
        withheld by the broker and not tax-deductible.
        """
        commission = max(
            (transaction_value_idr * self.SELL_COMMISSION_PCT).quantize(Decimal("1"), ROUND_HALF_UP),
            self.MIN_COMMISSION_IDR,
        )
        idx_levy = (transaction_value_idr * self.IDX_LEVY_PCT).quantize(Decimal("1"), ROUND_HALF_UP)
        vat = (commission * self.VAT_ON_COMMISSION).quantize(Decimal("1"), ROUND_HALF_UP)
        pph = (transaction_value_idr * self.PPH_SELL_PCT).quantize(Decimal("1"), ROUND_HALF_UP)
        total = commission + idx_levy + vat + pph
        effective_pct = (
            (total / transaction_value_idr * 100).quantize(Decimal("0.0001"), ROUND_HALF_UP)
            if transaction_value_idr > 0
            else Decimal("0")
        )

        return TransactionCost(
            transaction_value_idr=transaction_value_idr,
            commission_idr=commission,
            idx_levy_idr=idx_levy,
            vat_idr=vat,
            pph_idr=pph,
            total_cost_idr=total,
            effective_cost_pct=effective_pct,
        )

    def compute_breakeven_return(self, transaction_value_idr: Decimal) -> Decimal:
        """Minimum return to cover round-trip transaction costs.

        breakeven = (total_buy_cost + total_sell_cost) / transaction_value
        """
        buy = self.compute_buy_cost(transaction_value_idr)
        sell = self.compute_sell_cost(transaction_value_idr)
        if transaction_value_idr <= 0:
            return Decimal("0")
        return ((buy.total_cost_idr + sell.total_cost_idr) / transaction_value_idr).quantize(
            Decimal("0.000001"), ROUND_HALF_UP
        )
